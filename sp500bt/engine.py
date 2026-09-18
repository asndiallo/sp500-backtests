"""Strategy engine: lots, rules, corporate actions, and the simulation loop.

Generalises the notebook's original ``simulate()``:
  * pickers return ``[(ticker, weight), ...]`` so top-1 and top-10 share one loop;
  * corporate actions are value-based (see sp500bt.corporate_actions);
  * every external dollar is recorded in a dated cashflow ledger so a proper XIRR
    can be computed (the old summary ignored the index leg's contributions and
    the buy-the-dip top-ups);
  * each lot remembers the confidence of the Phase 1 row that triggered its
    purchase, so ending value can be attributed to HIGH / MEDIUM / LOW rows;
  * portfolios are marked to market on the valuation date itself, not only on
    contribution dates.

Rules are evaluated on contribution dates only (quarterly), as in the original
framework: a 25% trailing stop means "at a quarterly check the lot is >= 25%
below its highest quarterly-check price since purchase".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import AS_OF_DATE, CONTRIB_AMOUNT, CONTRIB_FREQ, INDEX_TICKER, START_DATE
from .corporate_actions import active_events
from .mcap import nominal_price
from .metrics import xirr
from .prices import PriceDataError, adjusted_close


class PriceBook:
    """Cached total-return and nominal series with O(log n) as-of lookups."""

    def __init__(self):
        self._tr, self._nom = {}, {}

    @staticmethod
    def _asof(cache, key, loader, date) -> float:
        if key not in cache:
            s = loader(key).dropna().sort_index()
            cache[key] = (s.index.values, s.values.astype(float), s.name)
        idx, vals, _ = cache[key]
        i = np.searchsorted(idx, np.datetime64(pd.Timestamp(date)), side="right") - 1
        if i < 0:
            raise PriceDataError(f"No {key} price on or before {pd.Timestamp(date).date()}")
        return float(vals[i])

    def tr(self, ticker, date) -> float:
        return self._asof(self._tr, ticker, adjusted_close, date)

    def nominal(self, ticker, date) -> float:
        return self._asof(self._nom, ticker, nominal_price, date)


@dataclass
class Lot:
    ticker: str
    shares: float
    purchase_date: pd.Timestamp
    purchase_price: float
    origin_confidence: str
    origin_date: pd.Timestamp
    kind: str = "contribution"          # or "dip_add"
    base_amount: float = 0.0            # dollars of the original purchase (sizes dip top-ups)
    peak_price: float = 0.0
    closed: bool = False
    dip_flags: set = field(default_factory=set)
    history: list = field(default_factory=list)  # ticker lineage through corporate actions

    def __post_init__(self):
        self.peak_price = self.peak_price or self.purchase_price
        self.history = self.history or [self.ticker]

    def value(self, price: float) -> float:
        return self.shares * price


# ---------------------------------------------------------------- rules
def rule_baseline_hold(lot, price_today):
    return "hold"


def rule_trailing_stop_25(lot, price_today, stop=0.25):
    lot.peak_price = max(lot.peak_price, price_today)
    return "sell_to_index" if price_today <= lot.peak_price * (1 - stop) else "hold"


def rule_buy_the_dip(lot, price_today, thresholds=(0.25, 0.50), adds_can_trigger=False):
    """Add ``add_amount`` of new money the first time a lot is 25% / 50% below its
    peak. By default top-up lots do not themselves trigger further top-ups (the
    original notebook let them, which compounds into a cascade of new money)."""
    if lot.kind == "dip_add" and not adds_can_trigger:
        return "hold"
    lot.peak_price = max(lot.peak_price, price_today)
    dd = 1 - price_today / lot.peak_price
    for t in thresholds:
        if dd >= t and t not in lot.dip_flags:
            lot.dip_flags.add(t)
            return f"add_{int(t * 100)}"
    return "hold"


RULES = {"baseline_hold": rule_baseline_hold, "trailing_stop_25": rule_trailing_stop_25,
         "buy_the_dip_25_50": rule_buy_the_dip}


# ---------------------------------------------------------------- simulation
@dataclass
class SimResult:
    lots: list
    index_units: dict            # origin -> units of the index series
    ledger: pd.DataFrame         # external cashflows: date, leg, amount (positive = money in)
    valuations: pd.DataFrame     # per contribution date + final valuation date
    events: pd.DataFrame         # corporate actions / rule actions that fired (+ origin_date of the lot)
    end: pd.Timestamp
    final: dict
    positions: pd.DataFrame      # every share change: date, symbol, shares, leg ("strategy" | "index_leg")

    def xirr(self, leg: str | None = None) -> float:
        """leg=None: whole portfolio; "stock": the #1-stock strategy leg (incl. index
        units bought with its own stop/deal proceeds); "index": the index leg."""
        led = self.ledger if leg is None else self.ledger[self.ledger.leg.str.startswith(leg)]
        terminal = self.final["total"] if leg is None else self.final[{"stock": "strategy_value",
                                                                      "index": "index_leg_value"}[leg]]
        flows = pd.concat([-led.set_index("date")["amount"], pd.Series({self.end: terminal})])
        return xirr(flows)


def contribution_dates(start=START_DATE, end=AS_OF_DATE, freq=CONTRIB_FREQ):
    return pd.date_range(start=start, end=end, freq=freq)


def simulate(picker, rule_fn, holdings: pd.DataFrame, corp_actions: pd.DataFrame, *,
             start=START_DATE, end=AS_OF_DATE, contrib=CONTRIB_AMOUNT, freq=CONTRIB_FREQ,
             index_ticker=INDEX_TICKER, add_amount=None, prices: PriceBook | None = None,
             label="scenario") -> SimResult:
    """Run one scenario.

    picker(date, holdings) -> (row, [(ticker, weight), ...]); ``row`` is the Phase 1
    table row used (for its confidence).
    rule_fn(lot, price_today) -> "hold" | "sell_to_index" | "add_25" | "add_50".
    add_amount: dollars per dip top-up; None (default) = the triggering lot's original
    purchase amount ($500 for top-1, $50 for a top-10 slice), so a top-up never
    exceeds the position it tops up.
    """
    px = prices or PriceBook()
    events_by_ticker = active_events(corp_actions)
    end = pd.Timestamp(end)
    lots: list[Lot] = []
    index_units: dict[str, float] = {}
    ledger, vals, fired, positions = [], [], [], []

    def to_index(amount, date, origin):
        units = amount / px.tr(index_ticker, date)
        index_units[origin] = index_units.get(origin, 0.0) + units
        positions.append((date, index_ticker, units, "index_leg" if origin == "contribution" else "strategy"))

    def apply_corp_actions(date):
        new_lots = []
        for lot in lots:
            while not lot.closed and lot.ticker in events_by_ticker:
                pending = [g for g in events_by_ticker[lot.ticker]
                           if lot.purchase_date < g.event_date.iloc[0] <= date]
                if not pending:
                    break
                g = pending[0]
                ev_date = g.event_date.iloc[0]
                value = lot.value(px.tr(lot.ticker, ev_date))
                p_old_nom = px.nominal(lot.ticker, ev_date)
                lot.closed = True
                positions.append((ev_date, lot.ticker, -lot.shares, "strategy"))
                for r in g.itertuples():
                    if r.mode == "cash":
                        proceeds = value * r.cash_per_share / p_old_nom
                        to_index(proceeds, ev_date, f"corp_action:{lot.origin_confidence}")
                        fired.append((ev_date, lot.ticker, "cash", proceeds, lot.origin_date))
                        continue
                    if r.mode == "bankruptcy":
                        fired.append((ev_date, lot.ticker, "bankruptcy", -value, lot.origin_date))
                        continue
                    if r.mode == "writeoff":  # sensitivity only: fraction ``ratio`` of value lost
                        fired.append((ev_date, lot.ticker, "writeoff", -value * r.ratio, lot.origin_date))
                        continue
                    if r.mode == "stock":
                        mult = r.ratio * px.nominal(r.new_ticker, ev_date) / p_old_nom
                        new_value = value * mult
                    else:  # value_split
                        mult, new_value = r.ratio, value * r.ratio
                    p_new = px.tr(r.new_ticker, ev_date)
                    child = Lot(r.new_ticker, new_value / p_new, lot.purchase_date, lot.purchase_price,
                                lot.origin_confidence, lot.origin_date, lot.kind, lot.base_amount * mult,
                                peak_price=p_new * lot.peak_price / px.tr(lot.ticker, ev_date),
                                dip_flags=set(lot.dip_flags), history=lot.history + [r.new_ticker])
                    child.purchase_date = ev_date  # later events of the child start after this one
                    new_lots.append(child)
                    positions.append((ev_date, r.new_ticker, child.shares, "strategy"))
                    fired.append((ev_date, lot.ticker, f"{r.mode}->{r.new_ticker} (x{mult:.4f})", new_value,
                                  lot.origin_date))
        lots.extend(new_lots)
        if new_lots:  # children may themselves have later events (e.g. T_CORP -> T in 2005)
            apply_corp_actions(date)

    for dt in contribution_dates(start, end, freq):
        apply_corp_actions(dt)
        # 1) rules on open lots
        for lot in list(lots):
            if lot.closed or lot.ticker == index_ticker:  # index-proxy lots are not subject to rules
                continue
            p = px.tr(lot.ticker, dt)
            action = rule_fn(lot, p)
            if action == "sell_to_index":
                to_index(lot.value(p), dt, f"stop_proceeds:{lot.origin_confidence}")
                lot.closed = True
                positions.append((dt, lot.ticker, -lot.shares, "strategy"))
                fired.append((dt, lot.ticker, "trailing_stop_sell", lot.value(p), lot.origin_date))
            elif action.startswith("add_"):
                amt = add_amount if add_amount is not None else lot.base_amount
                lots.append(Lot(lot.ticker, amt / p, dt, p, lot.origin_confidence, lot.origin_date, "dip_add", amt))
                positions.append((dt, lot.ticker, amt / p, "strategy"))
                ledger.append((dt, "stock_dip_add", amt))
                fired.append((dt, lot.ticker, action, amt, lot.origin_date))
        # 2) new contributions
        row, picks = picker(dt, holdings)
        for ticker, w in picks:
            p = px.tr(ticker, dt)
            lots.append(Lot(ticker, contrib * w / p, dt, p, row["confidence"], pd.Timestamp(row["date"]),
                            base_amount=contrib * w))
            positions.append((dt, ticker, contrib * w / p, "strategy"))
        ledger.append((dt, "stock", contrib))
        to_index(contrib, dt, "contribution")
        ledger.append((dt, "index", contrib))
        vals.append(_mark(dt, lots, index_units, px, index_ticker))

    apply_corp_actions(end)
    final = _mark(end, lots, index_units, px, index_ticker)
    vals.append(final)
    return SimResult(lots, index_units, pd.DataFrame(ledger, columns=["date", "leg", "amount"]),
                     pd.DataFrame(vals).set_index("date"),
                     pd.DataFrame(fired, columns=["date", "ticker", "action", "amount", "origin_date"]), end, final,
                     pd.DataFrame(positions, columns=["date", "symbol", "shares", "leg"]))


def _mark(date, lots, index_units, px, index_ticker) -> dict:
    eq = sum(lot.value(px.tr(lot.ticker, date)) for lot in lots if not lot.closed)
    p = px.tr(index_ticker, date)
    ix_leg = index_units.get("contribution", 0.0) * p
    ix_from_strategy = sum(u for k, u in index_units.items() if k != "contribution") * p
    return {"date": pd.Timestamp(date), "stock_lots_value": eq, "strategy_index_value": ix_from_strategy,
            "strategy_value": eq + ix_from_strategy, "index_leg_value": ix_leg,
            "total": eq + ix_from_strategy + ix_leg}


def attribution(res: SimResult, prices: PriceBook | None = None, index_ticker=INDEX_TICKER) -> pd.DataFrame:
    """Ending value split by the confidence of the Phase 1 row that triggered the
    original purchase (stock lots, plus index units bought with their proceeds)."""
    px = prices or PriceBook()
    rows: dict[str, float] = {}
    for lot in res.lots:
        if not lot.closed:
            rows[lot.origin_confidence] = rows.get(lot.origin_confidence, 0.0) + lot.value(px.tr(lot.ticker, res.end))
    ixp = px.tr(index_ticker, res.end)
    for origin, units in res.index_units.items():
        if origin != "contribution":
            conf = origin.split(":")[1]
            rows[conf] = rows.get(conf, 0.0) + units * ixp
    return pd.Series(rows, name="ending_value").sort_index()

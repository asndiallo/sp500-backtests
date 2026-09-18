"""Daily valuation of a finished simulation, time-weighted unit values, drawdowns,
and the cutoff reconciliation used to cross-check windowed runs.

The engine only marks portfolios on contribution dates; charts need daily values.
``daily_values`` replays the engine's position log (every share change, with its
date) on a business-day grid and prices it with the same total-return series.

A DCA portfolio's dollar value keeps rising with new money, which hides losses.
``unit_value`` strips external cashflows out (time-weighted return index), so
``sp500bt.metrics.drawdown`` measures what the stock leg itself lost from its peak.
"""
from __future__ import annotations

import pandas as pd

from .config import INDEX_TICKER
from .engine import PriceBook, SimResult
from .prices import adjusted_close

STRATEGY_EVENTS = ("trailing_stop_sell", "cash")  # events that move strategy money into the index


def daily_values(res: SimResult, start) -> pd.DataFrame:
    """Daily value of the strategy leg and the index leg (columns ``strategy``,
    ``index_leg``) from ``start`` to the valuation date. Manual month-end series
    (old AT&T, AT&T Corp) are forward-filled between prints."""
    pos = res.positions
    # the valuation date is always on the grid: a window can end on a weekend on which a
    # manual month-end series (e.g. T_CORP 1985-03-31) has a print the engine marks at
    grid = pd.bdate_range(start, res.end).union(pd.DatetimeIndex(pos.date.unique())).union([res.end])
    grid = grid[(grid >= pd.Timestamp(start)) & (grid <= res.end)]
    out = {}
    for leg, name in (("strategy", "strategy"), ("index_leg", "index_leg")):
        p = pos[pos.leg == leg]
        shares = (p.pivot_table(index="date", columns="symbol", values="shares", aggfunc="sum")
                  .reindex(grid, fill_value=0.0).fillna(0.0).cumsum())
        value = pd.Series(0.0, index=grid)
        for sym in shares.columns:
            px = adjusted_close(sym)
            px = px.reindex(px.index.union(grid)).ffill().reindex(grid)
            value += (shares[sym] * px).fillna(0.0)
        out[name] = value
    df = pd.DataFrame(out)
    for col, key in (("strategy", "strategy_value"), ("index_leg", "index_leg_value")):
        if abs(df[col].iloc[-1] / res.final[key] - 1) > 1e-9:
            raise AssertionError(f"daily {col} value does not reconcile to the engine's final mark")
    return df


def unit_value(values: pd.Series, flows: pd.Series) -> pd.Series:
    """Time-weighted unit value: r_t = (V_t - F_t) / V_{t-1} - 1, where F_t is the
    external money added on day t. Starts at 1 on the first funded day."""
    flows = flows.groupby(level=0).sum().reindex(values.index, fill_value=0.0)
    nav, level, prev = [], None, 0.0
    for v, f in zip(values.values, flows.values, strict=True):
        if level is None:
            level = 1.0 if v > 0 else None
        elif prev > 0:
            level *= (v - f) / prev
        nav.append(level)
        prev = v
    return pd.Series(nav, index=values.index, dtype=float)


def strategy_flows(res: SimResult) -> pd.Series:
    led = res.ledger[res.ledger.leg.str.startswith("stock")]
    return led.groupby("date")["amount"].sum()


def index_flows(res: SimResult) -> pd.Series:
    return res.ledger[res.ledger.leg == "index"].groupby("date")["amount"].sum()


def leg_navs(res: SimResult, daily: pd.DataFrame) -> dict[str, pd.Series]:
    """Time-weighted unit values of the stock leg (``strategy``, incl. index money its
    rule moved there), the index leg and the combined portfolio."""
    s_flows, i_flows = strategy_flows(res), index_flows(res)
    return {"stock": unit_value(daily["strategy"], s_flows),
            "index": unit_value(daily["index_leg"], i_flows),
            "combined": unit_value(daily["strategy"] + daily["index_leg"], s_flows.add(i_flows, fill_value=0.0))}


def subset_since(res: SimResult, cutoff, px: PriceBook, index_ticker=INDEX_TICKER) -> dict:
    """What a long run holds from lots first bought on/after ``cutoff`` (their open
    positions plus index units bought with their stop/deal proceeds), valued at
    ``res.end``. Rules act per lot, so this should equal a fresh run started at
    ``cutoff`` exactly."""
    cutoff, end = pd.Timestamp(cutoff), res.end
    open_value = sum(lot.value(px.tr(lot.ticker, end)) for lot in res.lots
                     if not lot.closed and lot.origin_date >= cutoff)
    ev = res.events[(res.events.origin_date >= cutoff) & res.events.action.isin(STRATEGY_EVENTS)]
    ix_end = px.tr(index_ticker, end)
    proceeds_value = sum(a * ix_end / px.tr(index_ticker, d) for d, a in zip(ev.date, ev.amount, strict=True))
    led = res.ledger[res.ledger.date >= cutoff]
    dip = res.events[(res.events.origin_date >= cutoff) & res.events.action.str.startswith("add_")]
    return {"strategy_value": open_value + proceeds_value,
            "strategy_invested": led[led.leg == "stock"].amount.sum() + dip.amount.sum(),
            "index_leg_value": sum(a * ix_end / px.tr(index_ticker, d)
                                   for d, a in zip(led[led.leg == "index"].date, led[led.leg == "index"].amount,
                                                   strict=True))}

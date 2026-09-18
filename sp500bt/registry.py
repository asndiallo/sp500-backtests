"""Named, parameterised building blocks that scenario configs refer to.

A scenario file says e.g. ``picker = { name = "confidence_gate", allowed = ["HIGH"] }``;
the runner looks the name up here and calls the factory with the remaining keys.
Adding a scenario that reuses existing blocks needs no code; a genuinely new
picker / rule / corporate-action treatment is one registered factory here.

Factories return fresh objects per run, so stateful pickers or rules never leak
state between runs.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from .config import INDEX_TICKER
from .engine import rule_baseline_hold, rule_buy_the_dip, rule_partial_trim, rule_trailing_stop_25
from .holdings import make_confidence_gate, row_on, top1_alt_picker, top1_picker, top10_picker

PICKERS: dict[str, Callable] = {}
RULES: dict[str, Callable] = {}
CORP_ACTIONS: dict[str, Callable] = {}


def register(table: dict, name: str):
    def deco(fn):
        if name in table:
            raise KeyError(f"duplicate registration {name!r}")
        table[name] = fn
        return fn
    return deco


def build(table: dict, spec: dict | str, kind: str):
    """``spec`` is a name or ``{name = ..., **params}`` from a scenario config."""
    spec = {"name": spec} if isinstance(spec, str) else dict(spec)
    name = spec.pop("name")
    if name not in table:
        raise KeyError(f"unknown {kind} {name!r}; registered: {sorted(table)}")
    return table[name](**spec)


# ------------------------------------------------------------------ pickers
@register(PICKERS, "top1")
def _top1():
    return top1_picker


@register(PICKERS, "top1_alt_on_low")
def _top1_alt():
    return top1_alt_picker


@register(PICKERS, "confidence_gate")
def _gate(allowed: list[str], fallback: str = INDEX_TICKER):
    return make_confidence_gate(set(allowed), fallback)


@register(PICKERS, "top1_index_before")
def _index_before(before: str, fallback: str = INDEX_TICKER):
    """#1 from ``before`` onward; the stock-leg money goes to ``fallback`` before it."""
    cutoff = pd.Timestamp(before)

    def picker(date, holdings):
        row = row_on(date, holdings)
        return row, [(fallback if pd.Timestamp(date) < cutoff else row["top1_ticker"], 1.0)]
    return picker


@register(PICKERS, "top10_ew")
def _top10():
    return top10_picker


@register(PICKERS, "random_from_top10")
def _random_top10(seed: int):
    """Placebo: each quarter one ticker drawn uniformly from that quarter's COMPLETE
    top-10 list (the #1 itself included). One seeded generator per run."""
    rng = np.random.default_rng(seed)

    def picker(date, holdings):
        row = row_on(date, holdings)
        tickers = _complete_top10(row)
        return row, [(tickers[int(rng.integers(len(tickers)))], 1.0)]
    return picker


def _complete_top10(row) -> list[str]:
    if row["top10_status"] != "COMPLETE":
        raise ValueError(f"top-10 list for {row['date'].date()} is {row['top10_status']}")
    return row["top10_tickers"].split(",")  # ordered by market cap (checked: [0] == #1, [1] == runner-up)


@register(PICKERS, "top1_margin_buffer")
def _margin_buffer(buffer: float = 0.05):
    """Hysteresis on the #1: keep buying the incumbent until a new #1 leads it by more than
    ``buffer`` in market cap at the observation date (new_cap / incumbent_cap - 1 > buffer).

    The incumbent's cap comes from the committed table: when it is the runner-up, the
    comparison is the row's ``margin_pct``. When it has dropped out of the top two its cap is
    not in the table, and the buffer is treated as exceeded (a #3 trails the #1 by at least the
    #1-#2 margin). That case occurs once, 2025-06-30: NVDA led AAPL by 26% (quarter-end caps in
    data/sources/derived_quarter_end_market_caps.csv), well over any buffer tested.
    Four LOW rows name a #1 whose estimated cap is slightly *below* the runner-up's (margin_pct
    -0.1 to -1.0: the #1 was set by source anchors, within the estimate's error); an incumbent
    runner-up is kept there at any buffer.
    Only new contributions follow the incumbent; existing lots are never sold by the picker."""
    state: dict[str, str | None] = {"incumbent": None}

    def picker(date, holdings):
        row = row_on(date, holdings)
        inc, new = state["incumbent"], row["top1_ticker"]
        if inc != new and (inc is None or inc != row["runner_up_ticker"] or row["margin_pct"] / 100 > buffer):
            state["incumbent"] = new
        return row, [(state["incumbent"], 1.0)]
    return picker


@register(PICKERS, "rank")
def _rank(n: int = 2):
    """The n-th largest company each quarter. n = 2 uses the table's runner-up (every row,
    1975 onward); n >= 3 needs a COMPLETE top-10 list (2006-04-01 onward)."""
    def picker(date, holdings):
        row = row_on(date, holdings)
        t = row["top1_ticker"] if n == 1 else row["runner_up_ticker"] if n == 2 else _complete_top10(row)[n - 1]
        return row, [(t, 1.0)]
    return picker


@register(PICKERS, "ranks_ew")
def _ranks_ew(first: int = 2, last: int = 5):
    """Equal weight across ranks ``first``..``last`` (inclusive) of the COMPLETE top-10 list."""
    def picker(date, holdings):
        row = row_on(date, holdings)
        names = _complete_top10(row)[first - 1:last]
        return row, [(t, 1.0 / len(names)) for t in names]
    return picker


@register(PICKERS, "fundamental_rank")
def _fundamental_rank(growth_weight: float = 0.5, margin_weight: float = 0.5, max_age_days: int = 400,
                      min_coverage: int = 10):
    """Each quarter, the top-10 member with the best weighted rank on fiscal-YTD revenue growth
    and margin (sp500bt.fundamentals.rank_scores), using only SEC filings filed on or before the
    row's observation date. Raises if fewer than ``min_coverage`` members have data, so a
    run can never silently shrink its universe."""
    from .fundamentals import rank_scores

    def picker(date, holdings):
        row = row_on(date, holdings)
        scores = rank_scores(_complete_top10(row), row["observation_date"], growth_weight, margin_weight,
                             max_age_days)
        covered = int(scores.score.notna().sum())
        if covered < min_coverage:
            raise ValueError(f"{row['date'].date()}: fundamentals for only {covered} of {len(scores)} top-10 names")
        return row, [(scores.ticker.iloc[0], 1.0)]
    return picker


# ------------------------------------------------------------------ rules
@register(RULES, "baseline_hold")
def _hold():
    return rule_baseline_hold


@register(RULES, "trailing_stop")
def _stop(stop: float = 0.25):
    if stop == 0.25:
        return rule_trailing_stop_25

    def rule(lot, price_today, date=None):
        return rule_trailing_stop_25(lot, price_today, stop=stop)
    return rule


@register(RULES, "buy_the_dip")
def _dip(thresholds: tuple[float, ...] | list[float] = (0.25, 0.50), adds_can_trigger: bool = False):
    th = tuple(thresholds)

    def rule(lot, price_today, date=None):
        return rule_buy_the_dip(lot, price_today, thresholds=th, adds_can_trigger=adds_can_trigger)
    return rule


@register(RULES, "partial_trim")
def _trim(drop: float = 0.25, fraction: float = 0.5, max_trims: int = 1):
    def rule(lot, price_today, date=None):
        return rule_partial_trim(lot, price_today, drop=drop, fraction=fraction, max_trims=max_trims)
    return rule


@register(RULES, "vol_scaled_stop")
def _vol_stop(k: float = 1.0, lookback_months: int = 36, floor: float = 0.10, cap: float = 0.50):
    """Trailing stop whose distance scales with the stock's own volatility:
    ``stop_t = clip(k * sigma_t, floor, cap)``, where sigma_t is the annualised standard
    deviation of the stock's monthly total returns over the ``lookback_months`` completed
    months before the check date (sqrt(12) scaling; monthly because the pre-1996 manual series are
    month-end prints). Sell when price <= peak * (1 - stop_t). Fewer than 12 months of
    history -> the cap applies."""
    from .metrics import annualized_volatility
    from .prices import adjusted_close

    cache: dict = {}

    def stop_for(ticker, date):
        key = (ticker, pd.Timestamp(date).to_period("M"))
        if key not in cache:
            px = adjusted_close(ticker)
            # completed months only: prices before the check date's month
            monthly = px[px.index < pd.Timestamp(date).to_period("M").start_time].resample("ME").last()
            monthly = monthly.pct_change().dropna()
            r = monthly.iloc[-lookback_months:]
            cache[key] = cap if len(r) < 12 else min(max(k * annualized_volatility(r, 12), floor), cap)
        return cache[key]

    def rule(lot, price_today, date=None):
        return rule_trailing_stop_25(lot, price_today, stop=stop_for(lot.ticker, date))
    return rule


# ------------------------------------------------------------------ corporate-action variants
@register(CORP_ACTIONS, "default")
def _ca_default():
    return lambda ca: ca


@register(CORP_ACTIONS, "att_sold_at_divestiture")
def _ca_att_sold(price: float = 61.43):
    """Liquidate old AT&T at its last pre-divestiture price; proceeds to the index leg."""
    def apply(ca: pd.DataFrame) -> pd.DataFrame:
        ca = ca[~((ca.old_ticker == "T_OLD") & (ca.event_date == "1984-01-01"))].copy()
        extra = pd.DataFrame([{"old_ticker": "T_OLD", "event_date": pd.Timestamp("1984-01-01"), "mode": "cash",
                               "cash_per_share": price, "new_ticker": "", "ratio": 0.0,
                               "notes": "sensitivity: sell at 1983-12-30 close", "source_url": ""}])
        return pd.concat([ca, extra], ignore_index=True)
    return apply


@register(CORP_ACTIONS, "att_uswest_writeoff")
def _ca_uswest(fraction: float = 0.089976):
    """Lower bound for the US West proxy: its share of old-AT&T value is lost."""
    def apply(ca: pd.DataFrame) -> pd.DataFrame:
        ca = ca.copy()
        m = (ca.old_ticker == "T_OLD") & (ca.event_date == "1984-01-01")
        ca.loc[m & (ca.new_ticker == "T"), "ratio"] -= fraction / 2
        ca.loc[m & (ca.new_ticker == "VZ"), "ratio"] -= fraction / 2
        extra = pd.DataFrame([{"old_ticker": "T_OLD", "event_date": pd.Timestamp("1984-01-01"),
                               "mode": "writeoff", "cash_per_share": 0.0, "new_ticker": "", "ratio": fraction,
                               "notes": "sensitivity: US West share written off", "source_url": ""}])
        return pd.concat([ca, extra], ignore_index=True)
    return apply

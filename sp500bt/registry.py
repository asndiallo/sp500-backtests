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
from .engine import rule_baseline_hold, rule_buy_the_dip, rule_trailing_stop_25
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
        if row["top10_status"] != "COMPLETE":
            raise ValueError(f"top-10 list for {row['date'].date()} is {row['top10_status']}")
        tickers = row["top10_tickers"].split(",")
        return row, [(tickers[int(rng.integers(len(tickers)))], 1.0)]
    return picker


# ------------------------------------------------------------------ rules
@register(RULES, "baseline_hold")
def _hold():
    return rule_baseline_hold


@register(RULES, "trailing_stop")
def _stop(stop: float = 0.25):
    if stop == 0.25:
        return rule_trailing_stop_25

    def rule(lot, price_today):
        return rule_trailing_stop_25(lot, price_today, stop=stop)
    return rule


@register(RULES, "buy_the_dip")
def _dip(thresholds: tuple[float, ...] | list[float] = (0.25, 0.50), adds_can_trigger: bool = False):
    th = tuple(thresholds)

    def rule(lot, price_today):
        return rule_buy_the_dip(lot, price_today, thresholds=th, adds_can_trigger=adds_can_trigger)
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

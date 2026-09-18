"""Registered post-processing hooks that scenario configs invoke via ``[[analyses]]``.

Signature: ``fn(ctx: sp500bt.run.Context, **params)``. Each writes into
``ctx.family.results_dir`` / ``ctx.family.charts_dir``.
"""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from . import charts
from .config import CONTRIB_AMOUNT
from .engine import attribution, contribution_dates
from .scenario import spec_label
from .timeseries import daily_values, drawdown, strategy_flows, subset_since, unit_value

ANALYSES: dict[str, Callable] = {}


def analysis(name: str):
    def deco(fn):
        ANALYSES[name] = fn
        return fn
    return deco


def _daily(ctx, run_id: str) -> pd.DataFrame:
    cache = ctx.__dict__.setdefault("_daily", {})
    if run_id not in cache:
        cache[run_id] = daily_values(ctx.sims[run_id], ctx.runs[run_id]["start"])
    return cache[run_id]


def _by_rule(ctx, run_ids: list[str]) -> dict[str, str]:
    """rule label -> run id (charts colour by rule)."""
    return {spec_label(ctx.runs[r]["rule"]): r for r in run_ids}


@analysis("attribution_by_confidence")
def attribution_by_confidence(ctx, runs: list[str], file: str = "attribution_by_confidence.csv"):
    """Ending value split by the confidence grade of the Phase 1 row behind each purchase."""
    cols = [attribution(ctx.sims[r], ctx.prices).rename(r) for r in runs]
    pd.concat(cols, axis=1).to_csv(ctx.family.results_dir / file)


@analysis("window_reconciliation")
def window_reconciliation(ctx, pairs: list[list[str]], cutoff: str, file: str = "window_reconciliation.csv"):
    """A fresh run started at ``cutoff`` must equal the long run's lots bought from ``cutoff``
    (rules act per lot). Raises if the values or the rule-trigger sets differ."""
    rows = []
    for short_id, long_id in pairs:
        fresh, full = ctx.sims[short_id], ctx.sims[long_id]
        from .report import summarize
        s = summarize(fresh)
        sub = subset_since(full, cutoff, ctx.prices)
        key = ["date", "ticker", "action"]
        ev95 = fresh.events
        ev75 = full.events[full.events.origin_date >= cutoff]
        row = {
            "rule": _by_rule(ctx, [short_id]).popitem()[0],
            "fresh_1995_strategy_value": s["strategy_value"],
            "1975_run_lots_bought_from_1995_value": sub["strategy_value"],
            "fresh_1995_strategy_invested": s["strategy_invested"],
            "1975_run_lots_bought_from_1995_invested": sub["strategy_invested"],
            "fresh_1995_index_leg": s["index_leg_value"], "1975_run_index_units_from_1995": sub["index_leg_value"],
            "rule_events_fresh": len(ev95), "rule_events_1975_run_same_lots": len(ev75),
            "event_sets_identical": sorted(map(tuple, ev95[key].astype(str).values))
            == sorted(map(tuple, ev75[key].astype(str).values)),
            "rule_events_1975_run_from_pre1995_lots_after_1995": int(
                ((full.events.date >= cutoff) & (full.events.origin_date < cutoff)).sum()),
        }
        gap = row["fresh_1995_strategy_value"] / row["1975_run_lots_bought_from_1995_value"] - 1
        if abs(gap) > 1e-9 or not row["event_sets_identical"]:
            raise AssertionError(f"{short_id} does not reconcile with {long_id}: gap {gap}")
        rows.append(row)
    pd.DataFrame(rows).to_csv(ctx.family.results_dir / file, index=False)


def _cum_contrib(start, idx):
    c = pd.Series(CONTRIB_AMOUNT, index=contribution_dates(start)).cumsum()
    return c.reindex(c.index.union(idx)).ffill().reindex(idx)


@analysis("growth_chart")
def growth_chart(ctx, runs: list[str], window: str, file: str):
    ctx.family.charts_dir.mkdir(parents=True, exist_ok=True)
    values = {rule: _daily(ctx, rid) for rule, rid in _by_rule(ctx, runs).items()}
    first = next(iter(values.values()))
    charts.growth_chart(values, window, ctx.family.charts_dir / file,
                        _cum_contrib(ctx.runs[runs[0]]["start"], first.index))


def _drawdowns(ctx, runs: list[str]) -> dict[str, pd.Series]:
    by_rule = _by_rule(ctx, runs)
    dd = {rule: drawdown(unit_value(_daily(ctx, rid)["strategy"], strategy_flows(ctx.sims[rid])))
          for rule, rid in by_rule.items()}
    ref = ctx.sims[runs[0]]
    idx_flows = ref.ledger.query("leg == 'index'").groupby("date")["amount"].sum()
    dd["index"] = drawdown(unit_value(_daily(ctx, runs[0])["index_leg"], idx_flows))
    return dd


@analysis("drawdown_chart")
def drawdown_chart(ctx, runs: list[str], window: str, file: str, max_drawdown_file: str | None = None):
    ctx.family.charts_dir.mkdir(parents=True, exist_ok=True)
    dd = _drawdowns(ctx, runs)
    events = {rule: ctx.sims[rid].events for rule, rid in _by_rule(ctx, runs).items()}
    charts.drawdown_chart(dd, events, window, ctx.family.charts_dir / file)
    if max_drawdown_file:
        maxdd = {r: (s.min(), s.idxmin().date()) for r, s in dd.items()}
        pd.DataFrame(maxdd, index=["max_drawdown", "date"]).T.to_csv(ctx.family.results_dir / max_drawdown_file)


@analysis("rule_events_chart")
def rule_events_chart(ctx, runs: list[str], window: str, file: str):
    ctx.family.charts_dir.mkdir(parents=True, exist_ok=True)
    by_rule = _by_rule(ctx, runs)
    values = {rule: _daily(ctx, rid) for rule, rid in by_rule.items()}
    events = {rule: ctx.sims[rid].events for rule, rid in by_rule.items()}
    charts.event_timeline(values, events, window, ctx.family.charts_dir / file)

"""Registered post-processing hooks that scenario configs invoke via ``[[analyses]]``.

Signature: ``fn(ctx: sp500bt.run.Context, **params)``. Each writes into
``ctx.family.results_dir`` / ``ctx.family.charts_dir``.
"""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from . import charts
from .config import CONTRIB_AMOUNT, CONTRIB_FREQ
from .engine import attribution, contribution_dates
from .metrics import drawdown, max_drawdown
from .scenario import spec_label
from .timeseries import index_flows, strategy_flows, subset_since, unit_value

ANALYSES: dict[str, Callable] = {}


def analysis(name: str):
    def deco(fn):
        ANALYSES[name] = fn
        return fn
    return deco


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
    values = {rule: ctx.daily(rid) for rule, rid in _by_rule(ctx, runs).items()}
    first = next(iter(values.values()))
    charts.growth_chart(values, window, ctx.family.charts_dir / file,
                        _cum_contrib(ctx.runs[runs[0]]["start"], first.index))


def _navs(ctx, runs: list[str]) -> dict[str, pd.Series]:
    """Stock-leg unit value per rule, plus the index leg of the first run."""
    navs = {rule: unit_value(ctx.daily(rid)["strategy"], strategy_flows(ctx.sims[rid]))
            for rule, rid in _by_rule(ctx, runs).items()}
    navs["index"] = unit_value(ctx.daily(runs[0])["index_leg"], index_flows(ctx.sims[runs[0]]))
    return navs


@analysis("drawdown_chart")
def drawdown_chart(ctx, runs: list[str], window: str, file: str, max_drawdown_file: str | None = None):
    ctx.family.charts_dir.mkdir(parents=True, exist_ok=True)
    navs = _navs(ctx, runs)
    events = {rule: ctx.sims[rid].events for rule, rid in _by_rule(ctx, runs).items()}
    charts.drawdown_chart({r: drawdown(n) for r, n in navs.items()}, events, window, ctx.family.charts_dir / file)
    if max_drawdown_file:
        mdd = {r: max_drawdown(n) for r, n in navs.items()}
        pd.DataFrame({r: (m["max_drawdown"], m["trough"].date()) for r, m in mdd.items()},
                     index=["max_drawdown", "date"]).T.to_csv(ctx.family.results_dir / max_drawdown_file)


@analysis("rule_events_chart")
def rule_events_chart(ctx, runs: list[str], window: str, file: str):
    ctx.family.charts_dir.mkdir(parents=True, exist_ok=True)
    by_rule = _by_rule(ctx, runs)
    values = {rule: ctx.daily(rid) for rule, rid in by_rule.items()}
    events = {rule: ctx.sims[rid].events for rule, rid in by_rule.items()}
    charts.event_timeline(values, events, window, ctx.family.charts_dir / file)


@analysis("pick_switches")
def pick_switches(ctx, runs: list[str] | None = None, file: str = "pick_switches.csv"):
    """How often each run's picker changes where new money goes. Picks are replayed from a
    fresh picker on the run's contribution dates (pickers do not depend on the rule), so a
    'switch' is a quarter whose set of picked tickers differs from the previous quarter's."""
    from .registry import PICKERS, build

    rows = []
    for rid in runs or list(ctx.runs):
        run, res = ctx.runs[rid], ctx.sims[rid]
        picker = build(PICKERS, run["picker"], "picker")
        dates = contribution_dates(run["start"], run.get("end", res.end), run.get("freq", CONTRIB_FREQ))
        picks = [frozenset(t for t, _ in picker(d, ctx.holdings)[1]) for d in dates]
        switches = sum(a != b for a, b in zip(picks, picks[1:], strict=False))
        spells = pd.Series([p != q for p, q in zip(picks, [None, *picks[:-1]], strict=True)]).cumsum()
        rows.append({"run": rid, "picker": spec_label(run["picker"]), "rule": spec_label(run["rule"]),
                     "start": run["start"], "contributions": len(picks), "switches": switches,
                     "distinct_tickers": len(frozenset().union(*picks)),
                     "mean_spell_periods": spells.value_counts().mean(),
                     "strategy_xirr": ctx.summary.set_index("scenario").loc[rid, "strategy_xirr"]})
    pd.DataFrame(rows).to_csv(ctx.family.results_dir / file, index=False)


@analysis("fundamental_scores")
def fundamental_scores(ctx, start: str, growth_weight: float = 0.5, margin_weight: float = 0.5,
                       max_age_days: int = 400, file: str = "fundamental_scores.csv"):
    """Every quarter's top-10 fundamentals, ranks and pick (audit trail for the picker)."""
    from .fundamentals import rank_scores
    from .holdings import row_on

    out = []
    for d in contribution_dates(start):
        row = row_on(d, ctx.holdings)
        sc = rank_scores(row["top10_tickers"].split(","), row["observation_date"], growth_weight, margin_weight,
                         max_age_days)
        out.append(sc.assign(date=d.date(), observation_date=row["observation_date"],
                             top1=row["top1_ticker"], picked=sc.index == 0))
    df = pd.concat(out, ignore_index=True)
    cols = ["date", "observation_date", "ticker", "picked", "top1", "cap_rank", "revenue_growth", "growth_rank",
            "margin", "margin_rank", "score", "margin_basis", "revenue_concept", "period_start", "period_end",
            "form", "filed"]
    df[cols].to_csv(ctx.family.results_dir / file, index=False)


@analysis("random_pick_placebo")
def random_pick_placebo(ctx, n_sims: int, base_seed: int, start: str, rule: str | dict = "baseline_hold",
                        reference: list[dict] | None = None):
    """Monte Carlo placebo: ``n_sims`` independent runs, each drawing one ticker per quarter
    uniformly from the COMPLETE top-10 list. Stores one summary row per run (no lot histories)
    and ranks each ``reference`` run (``{family, run, label}``) inside the distribution."""
    from .engine import simulate
    from .registry import PICKERS, RULES, build
    from .report import summarize
    from .risk import headline_risk

    rows = []
    for i in range(n_sims):
        seed = base_seed + i
        res = simulate(build(PICKERS, {"name": "random_from_top10", "seed": seed}, "picker"),
                       build(RULES, rule, "rule"), ctx.holdings, ctx.corp_actions, start=start, prices=ctx.prices)
        s = summarize(res)
        picks = [lot.ticker for lot in res.lots if lot.kind == "contribution"]
        top1 = [str(ctx.holdings.loc[ctx.holdings.date <= lot.purchase_date, "top1_ticker"].iloc[-1])
                for lot in res.lots if lot.kind == "contribution"]
        rows.append({"sim": i, "seed": seed, "strategy_xirr": s["strategy_xirr"], "strategy_value": s["strategy_value"],
                     "index_xirr": s["index_xirr"], "spread_vs_index": s["strategy_xirr"] - s["index_xirr"],
                     "distinct_tickers": len(set(picks)),
                     "share_quarters_drew_top1": sum(p == t for p, t in zip(picks, top1, strict=True)) / len(picks),
                     **headline_risk(res, start)})
    sims = pd.DataFrame(rows)
    out = ctx.family.results_dir
    sims.to_csv(out / "sims.csv", index=False)
    x = sims.strategy_xirr
    stats = {"n_sims": n_sims, "window_start": start, "mean": x.mean(), "median": x.median(), "std": x.std(ddof=1),
             "p05": x.quantile(0.05), "p25": x.quantile(0.25), "p75": x.quantile(0.75), "p95": x.quantile(0.95),
             "min": x.min(), "max": x.max(), "index_xirr": sims.index_xirr.iloc[0],
             "share_runs_beating_index": float((sims.spread_vs_index > 0).mean())}
    for k in ("stock_sharpe", "stock_sortino", "stock_max_drawdown"):
        stats |= {f"{k}_mean": sims[k].mean(), f"{k}_p05": sims[k].quantile(0.05),
                  f"{k}_median": sims[k].median(), f"{k}_p95": sims[k].quantile(0.95)}
    stats |= {"index_sharpe": sims.index_sharpe.iloc[0], "index_max_drawdown": sims.index_max_drawdown.iloc[0],
              "share_runs_sharpe_above_index": float((sims.stock_sharpe > sims.index_sharpe).mean())}
    refs = []
    for ref in reference or []:
        fam_dir = ctx.family.results_dir.parent / ref["family"]
        runs = pd.read_csv(fam_dir / "runs.csv", float_precision="round_trip").set_index("scenario")
        risk = pd.read_csv(fam_dir / "risk.csv").query("leg == 'stock'").set_index("scenario").loc[ref["run"]]
        v = float(runs.loc[ref["run"], "strategy_xirr"])
        refs.append({"label": ref["label"], "run": f"{ref['family']}/{ref['run']}", "strategy_xirr": v,
                     "percentile_rank": float((x < v).mean() * 100), "z_score": (v - stats["mean"]) / stats["std"],
                     "sharpe": risk.sharpe,
                     "sharpe_percentile_rank": float((sims.stock_sharpe < risk.sharpe).mean() * 100),
                     "max_drawdown": risk.max_drawdown,
                     "max_drawdown_percentile_rank": float((sims.stock_max_drawdown < risk.max_drawdown).mean() * 100)})
    pd.DataFrame([stats]).to_csv(out / "distribution_summary.csv", index=False)
    pd.DataFrame(refs).to_csv(out / "reference_ranks.csv", index=False)
    ctx.family.charts_dir.mkdir(parents=True, exist_ok=True)
    charts.placebo_histogram(sims, stats, refs, ctx.family.charts_dir / "xirr_distribution.png")
    print(f"  placebo: mean {stats['mean']:.2%} median {stats['median']:.2%} p5 {stats['p05']:.2%} "
          f"p95 {stats['p95']:.2%}; " + "; ".join(f"{r['label']} at P{r['percentile_rank']:.0f} "
                                                  f"(Sharpe P{r['sharpe_percentile_rank']:.0f})" for r in refs))


@analysis("tax_comparison")
def tax_comparison(ctx, pretax_family: str, pairs: list[list[str]], file: str = "tax_comparison.csv"):
    """Side-by-side pre-tax vs after-tax XIRRs. ``pairs`` = [[taxed_run_id, pretax_run_id], ...]
    where the pre-tax run lives in ``pretax_family``'s runs.csv (not re-simulated)."""
    pre = pd.read_csv(ctx.family.results_dir.parent / pretax_family / "runs.csv",
                      float_precision="round_trip").set_index("scenario")
    rows = []
    for taxed_id, pre_id in pairs:
        res, run, t = ctx.sims[taxed_id], ctx.runs[taxed_id], ctx.sims[taxed_id].tax
        p = pre.loc[pre_id]
        rows.append({
            "run": taxed_id, "rule": spec_label(run["rule"]), "start": run["start"],
            "lt_rate": t["lt_rate"], "st_rate": t["st_rate"],
            "pretax_strategy_xirr": p.strategy_xirr, "pretax_index_xirr": p.index_xirr,
            "strategy_xirr_interim_tax_only": res.xirr("stock"),
            "strategy_xirr_after_liquidation": res.xirr("stock", t["strategy_value_after_liquidation"]),
            "index_xirr_after_liquidation": res.xirr("index", t["index_leg_value_after_liquidation"]),
            "strategy_value_pretax": p.strategy_value, "strategy_value_interim_tax_only": res.final["strategy_value"],
            "strategy_value_after_liquidation": t["strategy_value_after_liquidation"],
            "index_value_after_liquidation": t["index_leg_value_after_liquidation"],
            "interim_tax_paid": t["interim_tax_paid"], "realizations": t["realizations"],
            "realized_gains": t["realized_gains"], "realized_losses": t["realized_losses"],
            "loss_carryforward_left": t["loss_carryforward_left"],
            "strategy_liquidation_tax": t["strategy_liquidation_tax"],
            "index_liquidation_tax": t["index_liquidation_tax"],
        })
    df = pd.DataFrame(rows)
    df.to_csv(ctx.family.results_dir / file, index=False)
    def order(g, col):
        return " > ".join(g.sort_values(col, ascending=False).rule)

    for (start, lt), g in df.groupby(["start", "lt_rate"]):
        print(f"  {start} lt={lt:.1%}: pre-tax {order(g, 'pretax_strategy_xirr')} | "
              f"after liquidation {order(g, 'strategy_xirr_after_liquidation')}")


@analysis("rolling_windows")
def rolling_windows(ctx, lengths: list[int], first_start: str, last_end: str,
                    picker: str | dict = "top1", rule: str | dict = "baseline_hold",
                    era_split: str = "1996-01-01", lag_threshold: float = 0.02):
    """For each window length L (years) and each quarter-start date s with s + L <= last_end, run a
    fresh DCA from s valued at the close before s + L; record (strategy XIRR - index XIRR)."""
    from .engine import simulate
    from .registry import PICKERS, RULES, build
    from .report import summarize
    from .risk import headline_risk

    rows = []
    for L in lengths:
        for s in pd.date_range(first_start, pd.Timestamp(last_end) - pd.DateOffset(years=L), freq="QS"):
            end = s + pd.DateOffset(years=L) - pd.Timedelta(days=1)
            res = simulate(build(PICKERS, picker, "picker"), build(RULES, rule, "rule"), ctx.holdings,
                           ctx.corp_actions, start=s, end=end, prices=ctx.prices)
            m = summarize(res)
            rows.append({"length_years": L, "start": s.date(), "valued_at": end.date(),
                         "contributions": m["contributions"], "strategy_xirr": m["strategy_xirr"],
                         "index_xirr": m["index_xirr"], "spread": m["strategy_xirr"] - m["index_xirr"],
                         **headline_risk(res, s)})
        print(f"  {L}-year windows done ({sum(r['length_years'] == L for r in rows)})")
    w = pd.DataFrame(rows)
    w["sharpe_spread"] = w.stock_sharpe - w.index_sharpe
    w.to_csv(ctx.family.results_dir / "windows.csv", index=False)
    era = pd.to_datetime(w.start) >= pd.Timestamp(era_split)
    groups = [("all", w)] + [(f"start < {era_split}", w[~era]), (f"start >= {era_split}", w[era])]
    summ = []
    for L in lengths:
        for name, g in groups:
            g = g[g.length_years == L]
            if g.empty:
                continue
            summ.append({"length_years": L, "starts": name, "windows": len(g), "mean_spread": g.spread.mean(),
                         "median_spread": g.spread.median(), "min_spread": g.spread.min(), "max_spread": g.spread.max(),
                         "share_beat_index": float((g.spread > 0).mean()),
                         f"share_lagged_by_more_than_{lag_threshold:.0%}": float((g.spread < -lag_threshold).mean()),
                         "share_within_1pp": float((g.spread.abs() <= 0.01).mean()),
                         "mean_sharpe_spread": g.sharpe_spread.mean(),
                         "share_sharpe_above_index": float((g.sharpe_spread > 0).mean()),
                         "share_max_dd_deeper_than_index": float((g.stock_max_drawdown < g.index_max_drawdown).mean())})
    pd.DataFrame(summ).to_csv(ctx.family.results_dir / "summary.csv", index=False)
    ctx.family.charts_dir.mkdir(parents=True, exist_ok=True)
    charts.rolling_spread(w, lengths, lag_threshold, era_split, ctx.family.charts_dir / "spread_by_start.png")

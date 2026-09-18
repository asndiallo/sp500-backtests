"""Generalised scenario runner.

    python -m sp500bt.run <family_id> [<family_id> ...]   run scenario families
    python -m sp500bt.run --all                            run every family in scenarios/
    python -m sp500bt.run --summary                        cross-family tables and charts
    python -m sp500bt.run --list                           manifest (scenarios/index.csv)

Outputs go to results/<family_id>/ (runs.csv, events/, analysis CSVs) and
charts/<family_id>/; cross-family artifacts to results/ and charts/summary/.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

import pandas as pd

from .config import AS_OF_DATE, CONTRIB_AMOUNT, CONTRIB_FREQ, INDEX_TICKER
from .corporate_actions import load_corporate_actions
from .engine import PriceBook, SimResult, simulate
from .holdings import load_top_holdings
from .registry import CORP_ACTIONS, PICKERS, RULES, build
from .report import summarize
from .scenario import Family, check_index, family_ids, load_family, load_index, spec_label


@dataclass
class Context:
    family: Family
    holdings: pd.DataFrame
    corp_actions: pd.DataFrame
    prices: PriceBook
    sims: dict[str, SimResult] = field(default_factory=dict)
    runs: dict[str, dict] = field(default_factory=dict)
    summary: pd.DataFrame | None = None


def simulate_run(run: dict, holdings: pd.DataFrame, ca: pd.DataFrame, px: PriceBook) -> SimResult:
    picker = build(PICKERS, run["picker"], "picker")
    rule = build(RULES, run["rule"], "rule")
    ca_variant = build(CORP_ACTIONS, run.get("corp_actions", "default"), "corp_actions")
    extra = {k: run[k] for k in ("tax", "check_freq", "rebuy") if k in run}
    return simulate(picker, rule, holdings, ca_variant(ca), start=run["start"], end=run.get("end", AS_OF_DATE),
                    contrib=run.get("contrib", CONTRIB_AMOUNT), freq=run.get("freq", CONTRIB_FREQ),
                    index_ticker=INDEX_TICKER, prices=px, label=run["id"], **extra)


def run_family(family_id: str, px: PriceBook | None = None, quiet: bool = False) -> Context:
    from .analyses import ANALYSES  # late import: analyses import charts/matplotlib

    fam = load_family(family_id)
    ctx = Context(fam, load_top_holdings(), load_corporate_actions(), px or PriceBook())
    fam.results_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for run in fam.runs:
        res = simulate_run(run, ctx.holdings, ctx.corp_actions, ctx.prices)
        ctx.sims[run["id"]] = res
        ctx.runs[run["id"]] = run
        rows.append(summarize(res, run["id"], group=run.get("group", fam.id), rule=spec_label(run["rule"]),
                              start=run["start"]))
        if run.get("outputs", {}).get("events", False):
            (fam.results_dir / "events").mkdir(exist_ok=True)
            res.events.to_csv(fam.results_dir / "events" / f"{run['id']}.csv", index=False)
        if not quiet:
            r = rows[-1]
            print(f"  {run['id']:46s} strategy XIRR {r['strategy_xirr']:.2%}  index XIRR {r['index_xirr']:.2%}")
    if rows:
        ctx.summary = pd.DataFrame(rows)
        ctx.summary.to_csv(fam.results_dir / "runs.csv", index=False)
    for a in fam.analyses:
        if a["name"] not in ANALYSES:
            raise KeyError(f"{fam.path}: unknown analysis {a['name']!r}; registered: {sorted(ANALYSES)}")
        ANALYSES[a["name"]](ctx, **a.get("params", {}))
    return ctx


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sp500bt.run", description=__doc__.split("\n\n")[0])
    ap.add_argument("families", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    problems = check_index()
    if problems:
        print("scenarios/index.csv is out of sync:\n  " + "\n  ".join(problems))
        return 2
    if args.list:
        print(load_index().to_string(index=False))
        return 0
    px = PriceBook()
    for fid in (family_ids() if args.all else args.families):
        print(f"[{fid}]")
        run_family(fid, px)
    if args.summary or args.all:
        from .summary import build_summary
        build_summary(px)
    return 0


if __name__ == "__main__":
    sys.exit(main())

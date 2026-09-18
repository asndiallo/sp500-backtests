"""Cross-family artifacts: results/scenario_comparison.csv and charts/summary/.

Rows are declared in scenarios/_summary.toml and read from each family's
results/<family>/runs.csv, so the summary never re-simulates anything.
"""
from __future__ import annotations

import tomllib

import pandas as pd

from . import charts
from .config import ROOT
from .engine import PriceBook
from .scenario import SCENARIOS_DIR

COMPARISON_COLUMNS = ["scenario", "window", "stock_leg_invested", "stock_leg_final", "stock_leg_xirr",
                      "index_leg_invested", "index_leg_final", "index_leg_xirr", "combined_final", "combined_xirr"]


def _load_summary_config() -> dict:
    with open(SCENARIOS_DIR / "_summary.toml", "rb") as f:
        return tomllib.load(f)


def _runs(family: str) -> pd.DataFrame:
    # round_trip: the default fast parser can drop the last bit of a float; summaries must carry
    # exactly the values the engine produced
    return pd.read_csv(ROOT / "results" / family / "runs.csv", float_precision="round_trip").set_index("scenario")


def comparison_table() -> pd.DataFrame:
    rows = []
    for spec in _load_summary_config()["comparison"]:
        s = _runs(spec["family"]).loc[spec["run"]]
        rows.append({"scenario": spec["label"], "window": spec["window"], "rule": spec["rule"],
                     "family": spec["family"], "run": spec["run"],
                     "stock_leg_invested": s.strategy_invested, "stock_leg_final": s.strategy_value,
                     "stock_leg_xirr": s.strategy_xirr, "index_leg_invested": s.index_invested,
                     "index_leg_final": s.index_leg_value, "index_leg_xirr": s.index_xirr,
                     "combined_final": s.total_value, "combined_xirr": s.total_xirr})
    return pd.DataFrame(rows)


def build_summary(px: PriceBook | None = None) -> pd.DataFrame:
    table = comparison_table()
    table[COMPARISON_COLUMNS].to_csv(ROOT / "results" / "scenario_comparison.csv", index=False)
    all_runs = pd.concat([pd.read_csv(p, float_precision="round_trip").assign(family=p.parent.name)
                          for p in sorted((ROOT / "results").glob("*/runs.csv"))], ignore_index=True)
    all_runs.to_csv(ROOT / "results" / "all_runs.csv", index=False)
    out = ROOT / "charts" / "summary"
    out.mkdir(parents=True, exist_ok=True)
    charts.xirr_bars(table, out / "xirr_by_window.png")
    print(f"wrote results/scenario_comparison.csv ({len(table)} rows), results/all_runs.csv "
          f"({len(all_runs)} runs) and charts/summary/")
    return table

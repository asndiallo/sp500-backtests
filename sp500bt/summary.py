"""Cross-family artifacts: results/scenario_comparison.csv, results/risk_metrics.csv,
results/extended_comparison.csv and charts/summary/.

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
RISK_COLUMNS = ["scenario", "window", "leg", "xirr", "twr_annualized", "volatility", "sharpe", "downside_deviation",
                "sortino", "max_drawdown", "max_dd_peak", "max_dd_trough", "max_dd_recovery", "underwater_days",
                "periods", "first_period", "last_period"]
LEG_XIRR = {"stock": "strategy_xirr", "index": "index_xirr", "combined": "total_xirr"}
EXTENDED_COLUMNS = ["section", "scenario", "window", "stock_leg_invested", "stock_leg_final", "stock_leg_xirr",
                    "index_leg_xirr", "spread_vs_index", "stock_sharpe", "index_sharpe", "stock_max_drawdown",
                    "index_max_drawdown", "family", "run"]


def _load_summary_config() -> dict:
    with open(SCENARIOS_DIR / "_summary.toml", "rb") as f:
        return tomllib.load(f)


def _read(family: str, name: str) -> pd.DataFrame:
    # round_trip: the default fast parser can drop the last bit of a float; summaries must carry
    # exactly the values the engine produced
    return pd.read_csv(ROOT / "results" / family / name, float_precision="round_trip")


def _runs(family: str) -> pd.DataFrame:
    return _read(family, "runs.csv").set_index("scenario")


def risk_table() -> pd.DataFrame:
    """Risk metrics of every leg of every comparison row, with the money-weighted XIRR alongside."""
    rows = []
    for spec in _load_summary_config()["comparison"]:
        runs, risk = _runs(spec["family"]), _read(spec["family"], "risk.csv")
        for _, r in risk[risk.scenario == spec["run"]].iterrows():
            rows.append({**r.to_dict(), "scenario": spec["label"], "window": spec["window"],
                         "xirr": runs.loc[spec["run"], LEG_XIRR[r.leg]]})
    return pd.DataFrame(rows)[RISK_COLUMNS]


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


def extended_table() -> pd.DataFrame:
    """Key variants from the later scenario families, with risk alongside XIRR."""
    rows = []
    for spec in _load_summary_config().get("extended", []):
        s = _runs(spec["family"]).loc[spec["run"]]
        risk = _read(spec["family"], "risk.csv").set_index(["scenario", "leg"])
        k, i = risk.loc[(spec["run"], "stock")], risk.loc[(spec["run"], "index")]
        rows.append({"section": spec["section"], "scenario": spec["label"], "window": spec["window"],
                     "stock_leg_invested": s.strategy_invested, "stock_leg_final": s.strategy_value,
                     "stock_leg_xirr": s.strategy_xirr, "index_leg_xirr": s.index_xirr,
                     "spread_vs_index": s.strategy_xirr - s.index_xirr, "stock_sharpe": k.sharpe,
                     "index_sharpe": i.sharpe, "stock_max_drawdown": k.max_drawdown,
                     "index_max_drawdown": i.max_drawdown, "family": spec["family"], "run": spec["run"]})
    return pd.DataFrame(rows, columns=EXTENDED_COLUMNS)


def build_summary(px: PriceBook | None = None) -> pd.DataFrame:
    table = comparison_table()
    table[COMPARISON_COLUMNS].to_csv(ROOT / "results" / "scenario_comparison.csv", index=False)
    all_runs = pd.concat([pd.read_csv(p, float_precision="round_trip").assign(family=p.parent.name)
                          for p in sorted((ROOT / "results").glob("*/runs.csv"))], ignore_index=True)
    all_runs.to_csv(ROOT / "results" / "all_runs.csv", index=False)
    risk = risk_table()
    risk.to_csv(ROOT / "results" / "risk_metrics.csv", index=False)
    all_risk = pd.concat([pd.read_csv(p).assign(family=p.parent.name)
                          for p in sorted((ROOT / "results").glob("*/risk.csv"))], ignore_index=True)
    all_risk.to_csv(ROOT / "results" / "all_risk.csv", index=False)
    extended = extended_table()
    extended.to_csv(ROOT / "results" / "extended_comparison.csv", index=False)
    out = ROOT / "charts" / "summary"
    out.mkdir(parents=True, exist_ok=True)
    charts.xirr_bars(table, out / "xirr_by_window.png")
    print(f"wrote results/scenario_comparison.csv ({len(table)} rows), risk_metrics.csv ({len(risk)} rows), "
          f"extended_comparison.csv ({len(extended)} rows), all_runs.csv ({len(all_runs)} runs), all_risk.csv "
          "and charts/summary/")
    return table

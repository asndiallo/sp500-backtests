"""Phases 7-9: fresh 1995-2026 runs, consolidated comparison table, charts.

* 1975-2026 rows and the top-10 row are taken from results/scenarios.csv (written by
  scripts/run_scenarios.py). They are re-simulated here only to obtain daily curves,
  and the re-run must reproduce the stored numbers exactly.
* 1995-2026 rows are NEW, independent backtests: $0 at 1995-01-01, $500/quarter per
  leg from 1995-01-01, same picker and rules, valued 2026-01-02. Not a slice of the
  1975 run.
* Cross-check: rules act per lot, so each fresh 1995 run must equal the 1975 run's
  lots first bought on/after 1995-01-01 (plus index units from their proceeds).

Run:  python scripts/compare_windows.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sp500bt import charts  # noqa: E402
from sp500bt.config import CONTRIB_AMOUNT, RESULTS_DIR, ROOT, START_DATE  # noqa: E402
from sp500bt.corporate_actions import load_corporate_actions  # noqa: E402
from sp500bt.engine import RULES, PriceBook, contribution_dates, simulate  # noqa: E402
from sp500bt.holdings import load_top_holdings, top1_picker, top10_picker  # noqa: E402
from sp500bt.report import summarize  # noqa: E402
from sp500bt.timeseries import daily_values, drawdown, strategy_flows, subset_since, unit_value  # noqa: E402

CHARTS_DIR = ROOT / "charts"
WINDOW_START = "1995-01-01"
TOP10_START = "2006-04-01"
W75, W95, W06 = "1975–2026", "1995–2026", "2006–2026 (from 2006-04-01)"
COLUMNS = ["scenario", "window", "stock_leg_invested", "stock_leg_final", "stock_leg_xirr", "index_leg_invested",
           "index_leg_final", "index_leg_xirr", "combined_final", "combined_xirr"]


def _row(s: dict, scenario: str, window: str, rule: str) -> dict:
    return {"scenario": scenario, "window": window, "rule": rule,
            "stock_leg_invested": s["strategy_invested"], "stock_leg_final": s["strategy_value"],
            "stock_leg_xirr": s["strategy_xirr"], "index_leg_invested": s["index_invested"],
            "index_leg_final": s["index_leg_value"], "index_leg_xirr": s["index_xirr"],
            "combined_final": s["total_value"], "combined_xirr": s["total_xirr"]}


def _check_same(stored: pd.Series, fresh: dict, what: str) -> None:
    for k in ("strategy_value", "index_leg_value", "strategy_xirr", "total_xirr"):
        if abs(fresh[k] / stored[k] - 1) > 1e-9:
            raise AssertionError(f"{what}: re-run {k}={fresh[k]} differs from results/scenarios.csv {stored[k]}")


def main() -> None:
    CHARTS_DIR.mkdir(exist_ok=True)
    holdings, ca, px = load_top_holdings(), load_corporate_actions(), PriceBook()
    stored = pd.read_csv(RESULTS_DIR / "scenarios.csv").set_index("scenario")
    rows, recon, runs75, runs95 = [], [], {}, {}

    for rule, fn in RULES.items():
        runs75[rule] = simulate(top1_picker, fn, holdings, ca, start=START_DATE, prices=px)
        _check_same(stored.loc[f"top1_{rule}"], summarize(runs75[rule]), f"top1_{rule} 1975")
        rows.append(_row(stored.loc[f"top1_{rule}"].to_dict(), charts.LABELS[rule], W75, rule))
    for rule, fn in RULES.items():
        runs95[rule] = simulate(top1_picker, fn, holdings, ca, start=WINDOW_START, prices=px)
        s = summarize(runs95[rule])
        rows.append(_row(s, charts.LABELS[rule], W95, rule))
        runs95[rule].events.to_csv(RESULTS_DIR / f"events_top1_{rule}_from_1995.csv", index=False)
        sub = subset_since(runs75[rule], WINDOW_START, px)
        ev95 = runs95[rule].events
        ev75 = runs75[rule].events[runs75[rule].events.origin_date >= WINDOW_START]
        key = ["date", "ticker", "action"]
        recon.append({
            "rule": rule, "fresh_1995_strategy_value": s["strategy_value"],
            "1975_run_lots_bought_from_1995_value": sub["strategy_value"],
            "fresh_1995_strategy_invested": s["strategy_invested"],
            "1975_run_lots_bought_from_1995_invested": sub["strategy_invested"],
            "fresh_1995_index_leg": s["index_leg_value"], "1975_run_index_units_from_1995": sub["index_leg_value"],
            "rule_events_fresh": len(ev95), "rule_events_1975_run_same_lots": len(ev75),
            "event_sets_identical": sorted(map(tuple, ev95[key].astype(str).values))
            == sorted(map(tuple, ev75[key].astype(str).values)),
            "rule_events_1975_run_from_pre1995_lots_after_1995": int(
                ((runs75[rule].events.date >= WINDOW_START) & (runs75[rule].events.origin_date < WINDOW_START)).sum()),
        })
    top10 = simulate(top10_picker, RULES["baseline_hold"], holdings, ca, start=TOP10_START, prices=px)
    _check_same(stored.loc["top10_ew_baseline_hold"], summarize(top10), "top10 baseline")
    rows.append(_row(stored.loc["top10_ew_baseline_hold"].to_dict(), charts.LABELS["top10"], W06, "top10"))

    table = pd.DataFrame(rows)
    table[COLUMNS].to_csv(RESULTS_DIR / "scenario_comparison.csv", index=False)
    rec = pd.DataFrame(recon)
    rec.to_csv(RESULTS_DIR / "window_reconciliation.csv", index=False)
    for r in recon:
        gap = r["fresh_1995_strategy_value"] / r["1975_run_lots_bought_from_1995_value"] - 1
        if abs(gap) > 1e-9 or not r["event_sets_identical"]:
            raise AssertionError(f"1995 run does not reconcile with the 1975 run for {r['rule']}: {gap}")

    # ---- charts
    daily95 = {r: daily_values(res, WINDOW_START) for r, res in runs95.items()}
    daily75 = {r: daily_values(res, START_DATE) for r, res in runs75.items()}

    def cum_contrib(start, idx):
        c = pd.Series(CONTRIB_AMOUNT, index=contribution_dates(start)).cumsum()
        return c.reindex(c.index.union(idx)).ffill().reindex(idx)

    charts.growth_chart(daily95, W95, CHARTS_DIR / "growth_1995_2026.png",
                        cum_contrib(WINDOW_START, daily95["baseline_hold"].index))
    charts.growth_chart(daily75, W75, CHARTS_DIR / "growth_1975_2026.png",
                        cum_contrib(START_DATE, daily75["baseline_hold"].index))
    dd = {r: drawdown(unit_value(daily95[r]["strategy"], strategy_flows(runs95[r]))) for r in runs95}
    idx_flows = runs95["baseline_hold"].ledger.query("leg == 'index'").groupby("date")["amount"].sum()
    dd["index"] = drawdown(unit_value(daily95["baseline_hold"]["index_leg"], idx_flows))
    events95 = {r: res.events for r, res in runs95.items()}
    charts.drawdown_chart(dd, events95, W95, CHARTS_DIR / "drawdown_1995_2026.png")
    charts.xirr_bars(table, CHARTS_DIR / "xirr_by_window.png")
    charts.event_timeline(daily95, events95, W95, CHARTS_DIR / "rule_events_1995_2026.png")
    maxdd = {r: (s.min(), s.idxmin().date()) for r, s in dd.items()}
    pd.DataFrame(maxdd, index=["max_drawdown", "date"]).T.to_csv(RESULTS_DIR / "max_drawdown_1995_2026.csv")

    fmt = table.copy()
    for c in ("stock_leg_invested", "stock_leg_final", "index_leg_invested", "index_leg_final", "combined_final"):
        fmt[c] = fmt[c].map(lambda v: f"${v:,.0f}")
    for c in ("stock_leg_xirr", "index_leg_xirr", "combined_xirr"):
        fmt[c] = fmt[c].map(lambda v: f"{v:.2%}")
    print("| " + " | ".join(COLUMNS) + " |\n|" + "---|" * len(COLUMNS))
    for r in fmt[COLUMNS].itertuples(index=False):
        print("| " + " | ".join(map(str, r)) + " |")
    print(rec.to_string())
    print(pd.DataFrame(maxdd, index=["max_drawdown", "date"]).T)


if __name__ == "__main__":
    main()

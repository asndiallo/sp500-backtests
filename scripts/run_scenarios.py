"""Phase 4: run every scenario and write results/ (CSV tables + chart).

Run:  python scripts/run_scenarios.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sp500bt.config import AS_OF_DATE, INDEX_TICKER, RESULTS_DIR, START_DATE  # noqa: E402
from sp500bt.corporate_actions import load_corporate_actions  # noqa: E402
from sp500bt.engine import RULES, PriceBook, attribution, simulate  # noqa: E402
from sp500bt.holdings import (  # noqa: E402
    load_top_holdings,
    make_confidence_gate,
    row_on,
    top1_alt_picker,
    top1_picker,
    top10_picker,
)
from sp500bt.report import summarize  # noqa: E402

TOP10_START = "2006-04-01"   # first quarter start with a COMPLETE top-10 list


def pre1996_to_index(date, holdings):
    row = row_on(date, holdings)
    t = INDEX_TICKER if pd.Timestamp(date) < pd.Timestamp("1996-01-01") else row["top1_ticker"]
    return row, [(t, 1.0)]


def att_sell_at_divestiture(ca: pd.DataFrame) -> pd.DataFrame:
    """Alternative corporate-action treatment: liquidate old AT&T at its last
    pre-divestiture price and roll the proceeds into the index leg."""
    ca = ca[~((ca.old_ticker == "T_OLD") & (ca.event_date == "1984-01-01"))].copy()
    extra = pd.DataFrame([{"old_ticker": "T_OLD", "event_date": pd.Timestamp("1984-01-01"), "mode": "cash",
                           "cash_per_share": 61.43, "new_ticker": "", "ratio": 0.0,
                           "notes": "sensitivity: sell at 1983-12-30 close", "source_url": ""}])
    return pd.concat([ca, extra], ignore_index=True)


def att_uswest_writeoff(ca: pd.DataFrame) -> pd.DataFrame:
    """Lower bound for the US West proxy: its 8.9976% of old-AT&T value is lost
    instead of tracking SBC/Bell Atlantic (the real path went via Qwest)."""
    ca = ca.copy()
    m = (ca.old_ticker == "T_OLD") & (ca.event_date == "1984-01-01")
    ca.loc[m & (ca.new_ticker == "T"), "ratio"] -= 0.044988
    ca.loc[m & (ca.new_ticker == "VZ"), "ratio"] -= 0.044988
    extra = pd.DataFrame([{"old_ticker": "T_OLD", "event_date": pd.Timestamp("1984-01-01"), "mode": "writeoff",
                           "cash_per_share": 0.0, "new_ticker": "", "ratio": 0.089976,
                           "notes": "sensitivity: US West share written off", "source_url": ""}])
    return pd.concat([ca, extra], ignore_index=True)


def scenario_specs(ca: pd.DataFrame) -> list[dict]:
    specs = []
    for rule in RULES:
        specs.append(dict(group="main", name=f"top1_{rule}", picker=top1_picker, rule=rule, ca=ca, start=START_DATE))
    for rule in RULES:
        specs.append(dict(group="top10", name=f"top10_ew_{rule}", picker=top10_picker, rule=rule, ca=ca,
                          start=TOP10_START))
        specs.append(dict(group="top10", name=f"top1_{rule}_from_2006", picker=top1_picker, rule=rule, ca=ca,
                          start=TOP10_START))
    high_only = make_confidence_gate({"HIGH"}, INDEX_TICKER)
    high_medium = make_confidence_gate({"HIGH", "MEDIUM"}, INDEX_TICKER)
    for rule in RULES:
        def spec(group, name, picker, actions=ca, start=START_DATE, rule=rule):
            return dict(group=group, name=f"{name}_{rule}", picker=picker, rule=rule, ca=actions, start=start)
        specs += [
            spec("data_sensitivity", "alt_on_LOW_rows", top1_alt_picker),
            spec("data_sensitivity", "only_HIGH_rows_buy_top1", high_only),
            spec("data_sensitivity", "HIGH_MEDIUM_rows_buy_top1", high_medium),
            spec("data_sensitivity", "pre1996_rows_to_index", pre1996_to_index),
            spec("window", "top1_from_1996", top1_picker, start="1996-01-01"),
            spec("corp_action_sensitivity", "att_sold_at_divestiture", top1_picker, att_sell_at_divestiture(ca)),
            spec("corp_action_sensitivity", "att_uswest_written_off", top1_picker, att_uswest_writeoff(ca)),
        ]
    return specs


def main() -> None:
    holdings = load_top_holdings()
    ca = load_corporate_actions()
    px = PriceBook()
    rows, curves, attrib = [], {}, []
    for spec in scenario_specs(ca):
        res = simulate(spec["picker"], RULES[spec["rule"]], holdings, spec["ca"], start=spec["start"],
                       end=AS_OF_DATE, prices=px, label=spec["name"])
        rows.append(summarize(res, spec["name"], group=spec["group"], rule=spec["rule"], start=spec["start"]))
        if spec["group"] in ("main", "top10"):
            curves[spec["name"]] = res.valuations
            res.events.to_csv(RESULTS_DIR / f"events_{spec['name']}.csv", index=False)
        if spec["group"] == "main":
            a = attribution(res, px).rename(spec["name"])
            attrib.append(a)
        r = rows[-1]
        print(f"{spec['name']:48s} strategy XIRR {r['strategy_xirr']:.2%}  index XIRR {r['index_xirr']:.2%}")
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS_DIR / "scenarios.csv", index=False)
    pd.concat(attrib, axis=1).to_csv(RESULTS_DIR / "attribution_by_confidence.csv")

    fig, ax = plt.subplots(figsize=(11, 6))
    for name, v in curves.items():
        if name.startswith("top1_") and "from" not in name:
            ax.plot(v.index, v["strategy_value"], label=f"{name} (strategy leg)")
    first = next(iter(curves.values()))
    ax.plot(first.index, first["index_leg_value"], "k--", label="index leg ($500/qtr S&P 500 TR)")
    ax.set_yscale("log")
    ax.set_title("Quarterly $500 DCA, 1975-2026: #1 S&P 500 company vs index")
    ax.set_ylabel("USD (log)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "portfolio_value.png", dpi=130)
    print(f"wrote {RESULTS_DIR/'scenarios.csv'} ({len(out)} scenarios)")


if __name__ == "__main__":
    main()

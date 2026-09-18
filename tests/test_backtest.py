"""Regression checks for the backtest (runs offline from the parquet/manual caches).

Run:  python -m pytest tests/      or      python tests/test_backtest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sp500bt.corporate_actions import load_corporate_actions  # noqa: E402
from sp500bt.engine import RULES, PriceBook, contribution_dates, simulate  # noqa: E402
from sp500bt.holdings import load_top_holdings, row_on, top1_picker  # noqa: E402
from sp500bt.metrics import xirr  # noqa: E402
from sp500bt.timeseries import daily_values, subset_since  # noqa: E402

PX = PriceBook()
END = pd.Timestamp("2026-01-02")


def test_xirr_known_case():
    flows = pd.Series({pd.Timestamp("2020-01-01"): -1000.0, pd.Timestamp("2021-01-01"): 1100.0})
    assert abs(xirr(flows) - 0.0998) < 5e-4  # 366-day year -> slightly under 10%


def test_point_in_time_lookup():
    h = load_top_holdings()
    assert row_on("1975-02-15", h).top1_ticker == row_on("1975-01-01", h).top1_ticker
    assert (h["date"].diff().dropna() > pd.Timedelta(0)).all()


def test_baseline_matches_closed_form():
    """Engine value == sum over contributions of $500 x growth of the pick,
    with old-AT&T lots traced by hand through the 1984 split and 2005 merger."""
    h, tr = load_top_holdings(), PX.tr
    div, mrg = pd.Timestamp("1983-12-30"), pd.Timestamp("2005-11-18")
    m_stock = 0.77942 * PX.nominal("T", mrg) / PX.nominal("T_CORP", mrg)
    m_cash = 1.30 / PX.nominal("T_CORP", mrg)
    tcorp = (m_stock * tr("T", END) / tr("T", mrg) + m_cash * tr("SPX_TR", END) / tr("SPX_TR", mrg)) \
        * tr("T_CORP", mrg) / tr("T_CORP", div)
    basket = 0.286743 * tcorp + 0.463695 * tr("T", END) / tr("T", div) + 0.249561 * tr("VZ", END) / tr("VZ", div)
    expect = 0.0
    for d in contribution_dates():
        t = row_on(d, h).top1_ticker
        if t == "T_OLD":
            g = tr("T_OLD", div) / tr("T_OLD", d) * basket
        elif t == "T_CORP":
            g = tcorp * tr("T_CORP", div) / tr("T_CORP", d)
        else:
            g = tr(t, END) / tr(t, d)
        expect += 500 * g
    res = simulate(top1_picker, RULES["baseline_hold"], h, load_corporate_actions(), prices=PX)
    assert abs(res.final["strategy_value"] / expect - 1) < 1e-9


def test_corporate_actions_conserve_value():
    """At each event the children's value equals the parent's (x the merger multiplier)."""
    h = load_top_holdings()
    res = simulate(top1_picker, RULES["baseline_hold"], h, load_corporate_actions(), prices=PX,
                   end="1984-01-03")
    ev = res.events
    assert len(ev) and (ev.action.str.startswith("value_split")).all()
    closed = [lot for lot in res.lots if lot.closed and lot.ticker == "T_OLD"]
    parent_value = sum(lot.value(PX.tr("T_OLD", "1983-12-30")) for lot in closed)
    assert abs(ev.amount.sum() / parent_value - 1) < 2e-6  # published allocations sum to 0.999999


def test_index_leg_is_pure_dca():
    h = load_top_holdings()
    res = simulate(top1_picker, RULES["baseline_hold"], h, load_corporate_actions(), prices=PX)
    expect = sum(500 * PX.tr("SPX_TR", END) / PX.tr("SPX_TR", d) for d in contribution_dates())
    assert abs(res.final["index_leg_value"] / expect - 1) < 1e-9


def test_fresh_window_equals_subset_of_full_run():
    """A fresh 1995 start must equal the 1975 run's lots bought from 1995 (rules act per lot),
    and the daily replay must land on the engine's final mark (asserted inside daily_values)."""
    h, ca = load_top_holdings(), load_corporate_actions()
    for rule in ("trailing_stop_25", "buy_the_dip_25_50"):
        fresh = simulate(top1_picker, RULES[rule], h, ca, start="1995-01-01", prices=PX)
        full = simulate(top1_picker, RULES[rule], h, ca, prices=PX)
        sub = subset_since(full, "1995-01-01", PX)
        assert abs(fresh.final["strategy_value"] / sub["strategy_value"] - 1) < 1e-9
        daily_values(fresh, "1995-01-01")


# Verified values (committed results, 2026-09-18). Any refactor must reproduce them.
GOLDEN_TOP1_CORE = {
    "top1_baseline_hold": 2460375.313955369,
    "top1_trailing_stop_25": 5200079.1552609075,
    "top1_buy_the_dip_25_50": 5565831.850594893,
    "top1_baseline_hold_from_1995": 442341.39449868375,
    "top1_trailing_stop_25_from_1995": 488825.7341553997,
    "top1_buy_the_dip_25_50_from_1995": 1078641.7903558128,
}


def test_scenario_configs_reproduce_verified_values():
    from sp500bt.run import simulate_run
    from sp500bt.scenario import load_family

    fam = load_family("top1_core")
    h, ca = load_top_holdings(), load_corporate_actions()
    got = {r["id"]: simulate_run(r, h, ca, PX).final["strategy_value"] for r in fam.runs}
    for run_id, expected in GOLDEN_TOP1_CORE.items():
        assert abs(got[run_id] / expected - 1) < 1e-12, (run_id, got[run_id], expected)


def test_scenario_manifest_in_sync():
    from sp500bt.scenario import check_index, family_ids, load_family

    assert check_index() == []
    for fid in family_ids():
        load_family(fid)  # every config parses and validates


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")

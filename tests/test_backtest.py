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
from sp500bt.metrics import (  # noqa: E402
    downside_deviation,
    max_drawdown,
    periodic_returns,
    sharpe_ratio,
    sortino_ratio,
    xirr,
)
from sp500bt.timeseries import daily_values, leg_navs, subset_since, unit_value  # noqa: E402

PX = PriceBook()
END = pd.Timestamp("2026-01-02")


def test_xirr_known_case():
    flows = pd.Series({pd.Timestamp("2020-01-01"): -1000.0, pd.Timestamp("2021-01-01"): 1100.0})
    assert abs(xirr(flows) - 0.0998) < 5e-4  # 366-day year -> slightly under 10%


def test_risk_metrics_hand_computed():
    nav = pd.Series([1.0, 1.2, 0.9, 0.6, 1.3, 1.1],
                    index=pd.to_datetime(["2020-01-02", "2020-01-31", "2020-02-28", "2020-03-31", "2020-04-30",
                                          "2020-05-04"]))
    mdd = max_drawdown(nav)
    assert abs(mdd["max_drawdown"] + 0.5) < 1e-12  # 1.2 -> 0.6
    assert mdd["peak"] == pd.Timestamp("2020-01-31") and mdd["trough"] == pd.Timestamp("2020-03-31")
    assert mdd["recovery"] == pd.Timestamp("2020-04-30") and mdd["underwater_days"] == 90
    r = periodic_returns(nav, "ME")  # May is a 1-day stub and is dropped
    assert list(r.round(10)) == [0.2, -0.25, round(0.6 / 0.9 - 1, 10), round(1.3 / 0.6 - 1, 10)]
    rf = 0.001
    ex = r - rf
    assert abs(sharpe_ratio(r, rf, 12) - ex.mean() / ex.std(ddof=1) * 12 ** 0.5) < 1e-12
    dd = ((ex.clip(upper=0) ** 2).sum() / 4) ** 0.5 * 12 ** 0.5  # averaged over ALL periods
    assert abs(downside_deviation(r, rf, 12) - dd) < 1e-12
    assert abs(sortino_ratio(r, rf, 12) - ex.mean() * 12 / dd) < 1e-12


def test_unit_value_ignores_contributions():
    """Doubling the money in a flat market is not a return."""
    idx = pd.bdate_range("2020-01-01", periods=4)
    values = pd.Series([100.0, 110.0, 220.0, 198.0], index=idx)  # +10%, then +100 contributed, then -10%
    nav = unit_value(values, pd.Series({idx[0]: 100.0, idx[2]: 110.0}))
    assert list(nav.round(12)) == [1.0, 1.1, 1.1, 0.99]


def test_leg_navs_reconcile_to_engine():
    """The combined NAV must sit between the legs' NAVs each day (it is their value-weighted mix)."""
    res = simulate(top1_picker, RULES["baseline_hold"], load_top_holdings(), load_corporate_actions(),
                   start="2015-01-01", prices=PX)
    navs = leg_navs(res, daily_values(res, "2015-01-01"))
    r = {k: v.pct_change().dropna() for k, v in navs.items()}
    lo = pd.concat([r["stock"], r["index"]], axis=1).min(axis=1) - 1e-12
    hi = pd.concat([r["stock"], r["index"]], axis=1).max(axis=1) + 1e-12
    inside = (r["combined"] >= lo) & (r["combined"] <= hi)
    flow_days = res.ledger.date.unique()
    assert inside[~inside.index.isin(flow_days)].all()


def test_margin_buffer_zero_is_plain_top1():
    """With a 0% buffer the picker follows the #1, except on the 4 LOW rows whose #1 was set by
    source anchors against a (within-error) negative market-cap margin; there it keeps the
    incumbent until the next row."""
    from sp500bt.registry import PICKERS, build

    h = load_top_holdings()
    plain, buffered = build(PICKERS, "top1", "picker"), build(PICKERS, {"name": "top1_margin_buffer", "buffer": 0.0},
                                                             "picker")
    differ = [d for d in contribution_dates("1975-01-01") if plain(d, h)[1] != buffered(d, h)[1]]
    negative = set(h.loc[h.margin_pct <= 0, "date"])
    assert differ and all(row_on(d, h)["date"] in negative for d in differ), differ


def test_fundamentals_are_point_in_time():
    """Snapshots only use filings filed on or before the cut-off, and a later cut-off never
    changes an earlier quarter's snapshot."""
    from sp500bt.fundamentals import snapshot

    for cutoff in ["2013-03-31", "2018-06-30", "2024-09-30"]:
        for t in ["AAPL", "XOM", "JPM", "WFC", "BRK-B"]:
            snap = snapshot(t, pd.Timestamp(cutoff))
            if snap is not None:
                assert snap["filed"] <= pd.Timestamp(cutoff), (t, cutoff)
                assert (pd.Timestamp(cutoff) - snap["period_end"]).days <= 400


def test_stop_and_rebuy_conserves_value():
    """Rebuys only move strategy money between the index and the stock: no parked index units
    go negative, each stop is rebought at most once, and with no rebuys the run equals the
    plain trailing stop."""
    from sp500bt.registry import RULES as REG_RULES
    from sp500bt.registry import build

    h, ca = load_top_holdings(), load_corporate_actions()
    stop = build(REG_RULES, {"name": "trailing_stop", "stop": 0.25}, "rule")
    res = simulate(top1_picker, stop, h, ca, start="1995-01-01", prices=PX, rebuy={"require_loss_of_top": True})
    assert min(res.index_units.values()) > -1e-9
    ev = res.events
    assert (ev.action == "rebuy").sum() <= (ev.action == "trailing_stop_sell").sum()
    assert res.ledger.amount.sum() == simulate(top1_picker, stop, h, ca, start="1995-01-01",
                                               prices=PX).ledger.amount.sum()  # no new money
    never = simulate(top1_picker, stop, h, ca, start="1995-01-01", end="1996-12-31", prices=PX,
                     rebuy={"require_loss_of_top": True})
    plain = simulate(top1_picker, stop, h, ca, start="1995-01-01", end="1996-12-31", prices=PX)
    if not (never.events.action == "rebuy").any():
        assert abs(never.final["total"] - plain.final["total"]) < 1e-6


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

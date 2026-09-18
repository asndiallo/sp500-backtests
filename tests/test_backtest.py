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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")

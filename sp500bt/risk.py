"""Risk metrics per simulated run: glue between a SimResult, its daily valuation and
the pure functions in ``sp500bt.metrics``. Parameters come from ``sp500bt.config``
(RISK_FREQ, RISK_PERIODS_PER_YEAR, RISK_FREE)."""
from __future__ import annotations

from functools import cache

import pandas as pd

from .config import RISK_FREE, RISK_FREE_CSV, RISK_FREQ, RISK_PERIODS_PER_YEAR
from .engine import SimResult
from .metrics import risk_profile
from .timeseries import daily_values, leg_navs

LEGS = ("stock", "index", "combined")


@cache
def risk_free_returns(freq: str = RISK_FREQ, periods_per_year: int = RISK_PERIODS_PER_YEAR) -> pd.Series:
    """Per-period risk-free return labelled at period end (same labels as
    ``metrics.periodic_returns``)."""
    df = pd.read_csv(RISK_FREE_CSV, comment="#", parse_dates=["date"])
    annual = df.set_index("date")["tb3ms_pct"] / 100.0
    per = (1.0 + annual) ** (1.0 / periods_per_year) - 1.0
    return per.resample(freq).last()


def risk_free(freq: str = RISK_FREQ, periods_per_year: int = RISK_PERIODS_PER_YEAR) -> pd.Series | float:
    if isinstance(RISK_FREE, (int, float)):
        return (1.0 + RISK_FREE) ** (1.0 / periods_per_year) - 1.0
    if RISK_FREE != "tb3ms":
        raise ValueError(f"unknown RISK_FREE {RISK_FREE!r}")
    return risk_free_returns(freq, periods_per_year)


def risk_rows(res: SimResult, daily: pd.DataFrame, scenario: str) -> list[dict]:
    """One row per leg (stock / index / combined) with every metric in metrics.risk_profile."""
    rf = risk_free()
    return [{"scenario": scenario, "leg": leg, **risk_profile(nav, rf, RISK_FREQ, RISK_PERIODS_PER_YEAR)}
            for leg, nav in leg_navs(res, daily).items()]


HEADLINE = ("sharpe", "sortino", "max_drawdown")


def headline_risk(res: SimResult, start, legs=("stock", "index"), keys=HEADLINE) -> dict:
    """Flat ``{leg}_{metric}`` dict for bulk analyses (placebo, rolling windows) that keep
    one summary row per simulation."""
    rows = {r["leg"]: r for r in risk_rows(res, daily_values(res, start), "")}
    return {f"{leg}_{k}": rows[leg][k] for leg in legs for k in keys}

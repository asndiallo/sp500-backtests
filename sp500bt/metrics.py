"""Return and risk metrics.

* Money-weighted: ``xirr`` on dated cashflows (what an investor actually earned).
* Time-weighted / risk: functions on a unit-value series ``nav`` (external
  cashflows stripped out, see ``sp500bt.timeseries.unit_value``) and on the periodic
  returns sampled from it. XIRR alone says nothing about the path; these do.

All functions are pure (no I/O); the risk-free series and the sampling frequency
are passed in by the caller (``sp500bt.risk``), which reads them from config.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq


def xnpv(rate: float, flows: pd.Series) -> float:
    t0 = flows.index[0]
    years = (flows.index - t0).days / 365.25
    return float(np.sum(flows.values / (1.0 + rate) ** years))


def xirr(flows: pd.Series) -> float:
    """Annualised internal rate of return for irregular dated cashflows.

    ``flows`` is indexed by date; contributions negative, terminal value positive.
    Solved with Brent's method on [-99%, +1000%]."""
    flows = flows.groupby(level=0).sum().sort_index()
    if not ((flows < 0).any() and (flows > 0).any()):
        raise ValueError("xirr needs at least one negative and one positive cashflow")
    return brentq(lambda r: xnpv(r, flows), -0.99, 10.0, xtol=1e-10, maxiter=500)


# ------------------------------------------------------------------ drawdown
def drawdown(nav: pd.Series) -> pd.Series:
    """Fractional distance below the running peak (0 at a new high, -0.4 = 40% down)."""
    return nav / nav.cummax() - 1.0


def max_drawdown(nav: pd.Series) -> dict:
    """Deepest peak-to-trough fall of ``nav``: depth (negative fraction), the peak and
    trough dates, the first date the old peak was regained (NaT if never) and the
    peak-to-recovery length in days (NaN if not recovered)."""
    nav = nav.dropna()
    dd = drawdown(nav)
    trough = dd.idxmin()
    peak = nav.loc[:trough].idxmax()
    after = nav.loc[trough:]
    regained = after[after >= nav.loc[peak]]
    recovery = regained.index[0] if len(regained) else pd.NaT
    return {"max_drawdown": float(dd.min()), "peak": peak, "trough": trough, "recovery": recovery,
            "underwater_days": (recovery - peak).days if len(regained) else np.nan}


# ------------------------------------------------------------------ periodic returns
def periodic_returns(nav: pd.Series, freq: str = "ME") -> pd.Series:
    """Simple returns of ``nav`` per calendar period (``freq`` is a pandas offset alias,
    labelled at period end). The first period is measured from the first valued day;
    a trailing partial period (series ends before the period does) is dropped, so every
    return spans at most one full period."""
    nav = nav.dropna()
    levels = nav.resample(freq).last()
    if nav.index[-1] < levels.index[-1]:
        levels = levels.iloc[:-1]
    base = pd.Series([nav.iloc[0]], index=[nav.index[0] - pd.Timedelta(days=1)])
    return pd.concat([base, levels]).pct_change().iloc[1:]


def _excess(returns: pd.Series, rf: pd.Series | float) -> pd.Series:
    if isinstance(rf, pd.Series):
        rf = rf.reindex(returns.index)
        if rf.isna().any():
            raise ValueError(f"risk-free series missing for {rf[rf.isna()].index[:3].tolist()} ...")
    return returns - rf


def annualized_return(returns: pd.Series, periods_per_year: int) -> float:
    """Geometric (time-weighted) annual return: prod(1+r)^(ppy/n) - 1."""
    return float((1.0 + returns).prod() ** (periods_per_year / len(returns)) - 1.0)


def annualized_volatility(returns: pd.Series, periods_per_year: int) -> float:
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(returns: pd.Series, rf: pd.Series | float, periods_per_year: int) -> float:
    """mean(r - rf) / std(r - rf) * sqrt(ppy), on per-period excess returns."""
    ex = _excess(returns, rf)
    return float(ex.mean() / ex.std(ddof=1) * np.sqrt(periods_per_year))


def downside_deviation(returns: pd.Series, mar: pd.Series | float, periods_per_year: int) -> float:
    """sqrt(mean(min(r - mar, 0)^2)) * sqrt(ppy): the root-mean-square shortfall below the
    minimum acceptable return, averaged over ALL periods (not just the losing ones)."""
    short = np.minimum(_excess(returns, mar), 0.0)
    return float(np.sqrt((short ** 2).mean()) * np.sqrt(periods_per_year))


def sortino_ratio(returns: pd.Series, rf: pd.Series | float, periods_per_year: int) -> float:
    """Annualised mean excess return over the risk-free rate / downside deviation below it."""
    ex = _excess(returns, rf)
    return float(ex.mean() * periods_per_year / downside_deviation(returns, rf, periods_per_year))


def risk_profile(nav: pd.Series, rf: pd.Series | float, freq: str = "ME", periods_per_year: int = 12) -> dict:
    """Every risk metric for one unit-value series."""
    r = periodic_returns(nav, freq)
    mdd = max_drawdown(nav)
    return {"periods": len(r), "first_period": r.index[0].date(), "last_period": r.index[-1].date(),
            "twr_annualized": annualized_return(r, periods_per_year),
            "volatility": annualized_volatility(r, periods_per_year),
            "sharpe": sharpe_ratio(r, rf, periods_per_year),
            "downside_deviation": downside_deviation(r, rf, periods_per_year),
            "sortino": sortino_ratio(r, rf, periods_per_year),
            "max_drawdown": mdd["max_drawdown"], "max_dd_peak": mdd["peak"].date(),
            "max_dd_trough": mdd["trough"].date(),
            "max_dd_recovery": mdd["recovery"].date() if pd.notna(mdd["recovery"]) else None,
            "underwater_days": mdd["underwater_days"]}

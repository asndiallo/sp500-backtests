"""Long-run daily S&P 500 total-return index for the index leg.

^GSPC is a *price* index; using it alone would drop the ~3-6%/yr dividend yield of
the 1970s-80s. ^SP500TR (dividends reinvested) only starts on 1988-01-04. So:

* before the splice date: daily ^GSPC price return plus Shiller's dividend
  (``D`` column of ie_data.xls = annualised dividends per index unit, monthly),
  accrued evenly over that month's trading days;
* from the splice date on: ^SP500TR daily returns.

The same synthetic construction is also run over the overlap with ^SP500TR so
its tracking error can be reported (see ``validate``).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import MANUAL_PRICES_DIR, SOURCES_DIR
from .prices import load_yahoo_history

SHILLER_XLS = SOURCES_DIR / "shiller_ie_data.xls"
SHILLER_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
SPLICE_DATE = pd.Timestamp("1988-01-04")


def shiller_monthly() -> pd.DataFrame:
    raw = pd.read_excel(SHILLER_XLS, sheet_name="Data", header=None, skiprows=8)
    raw = raw.iloc[:, :3].dropna()
    raw.columns = ["date", "P", "D"]
    raw = raw[pd.to_numeric(raw["date"], errors="coerce").notna()]
    # Shiller encodes months as 1871.01 ... 1871.1 (= October) ... 1871.12
    yr = raw["date"].astype(float).apply(lambda v: int(v))
    mo = raw["date"].astype(float).apply(lambda v: int(round((v - int(v)) * 100)))
    idx = pd.PeriodIndex.from_fields(year=yr.values, month=mo.values, freq="M")
    return pd.DataFrame({"P": raw["P"].astype(float).values,
                         "D": pd.to_numeric(raw["D"], errors="coerce").values}, index=idx)


def synthetic_tr_returns(start="1970-01-01", end=None) -> pd.Series:
    """Daily total returns from ^GSPC price + Shiller dividends."""
    px = load_yahoo_history("^GSPC")["Close"].loc[start:end]
    divs = shiller_monthly()["D"].dropna()
    months = px.index.to_period("M")
    n_days = pd.Series(1, index=px.index).groupby(months).transform("count")
    d_annual = pd.Series(months.map(divs.to_dict()), index=px.index).astype(float)
    if d_annual.isna().any():
        missing = sorted({str(m) for m in months[d_annual.isna()]})
        raise ValueError(f"Shiller dividend missing for months {missing[:3]}...{missing[-3:]}")
    daily_div = d_annual / 12.0 / n_days
    r = (px + daily_div) / px.shift(1) - 1.0
    return r.dropna().rename("synthetic_tr_ret")


def build_spx_tr(start="1970-01-01") -> pd.Series:
    synth = synthetic_tr_returns(start, SPLICE_DATE)
    sptr = load_yahoo_history("^SP500TR")["Close"]
    tr_ret = sptr.pct_change().loc[SPLICE_DATE + pd.Timedelta(days=1):]
    rets = pd.concat([synth.loc[:SPLICE_DATE], tr_ret])
    level = (1.0 + rets).cumprod()
    # rescale so the level equals ^SP500TR's own print on the splice date
    level = level / level.loc[SPLICE_DATE] * float(sptr.loc[SPLICE_DATE])
    first = synth.index[0] - pd.tseries.offsets.BDay(1)
    return pd.concat([pd.Series({first: level.iloc[0] / (1 + rets.iloc[0])}), level]).rename("SPX_TR")


def validate(start=SPLICE_DATE, end="2023-06-30") -> dict:
    """Compare the synthetic method with ^SP500TR over their overlap."""
    synth = synthetic_tr_returns("1987-01-01", end).loc[start:end]
    sptr = load_yahoo_history("^SP500TR")["Close"].pct_change().loc[start:end]
    j = pd.concat([synth, sptr.rename("sptr")], axis=1).dropna()
    yrs = (j.index[-1] - j.index[0]).days / 365.25

    def cagr(r):
        return (1 + r).prod() ** (1 / yrs) - 1

    return {"years": round(yrs, 2), "synthetic_cagr": cagr(j.iloc[:, 0]),
            "sp500tr_cagr": cagr(j["sptr"]),
            "annual_tracking_diff": cagr(j.iloc[:, 0]) - cagr(j["sptr"]),
            "daily_corr": float(np.corrcoef(j.iloc[:, 0], j["sptr"])[0, 1])}


def write_manual_csv() -> None:
    s = build_spx_tr()
    path = MANUAL_PRICES_DIR / "SPX_TR.csv"
    with open(path, "w") as f:
        f.write("# S&P 500 total-return level. <1988-01-04: ^GSPC daily price return + Shiller "
                f"monthly dividends ({SHILLER_URL}) accrued daily; >=1988-01-04: ^SP500TR daily "
                "returns. Built by sp500bt.index_tr.write_manual_csv()\n")
        s.rename("close").rename_axis("date").to_frame().to_csv(f, float_format="%.6f")

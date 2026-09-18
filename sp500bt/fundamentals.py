"""Point-in-time fundamentals from SEC XBRL filings (data/sources/sec_xbrl_fundamentals.csv).

For a company and a cut-off date, ``snapshot`` uses only filings **filed on or before** the
cut-off. From the most recent usable 10-K/10-Q it takes the fiscal year-to-date figures
(the longest-duration facts ending at the filing's period end) and the prior-year
comparatives reported in the same filing:

* revenue growth  = YTD revenue / prior-year YTD revenue - 1. Revenue is the first
                    standard us-gaap revenue tag present (REVENUE_PRIORITY); banks that tag no
                    total revenue use net interest income + noninterest income
* margin          = YTD operating income / YTD revenue; companies that report no
                    OperatingIncomeLoss (banks, insurers, Berkshire) use pre-tax income

Both numbers come from one filing, so there is no mixing of restated and original values
and no seasonality (year-to-date vs the same span a year earlier). If the latest filings
carry no standard revenue tag (Exxon's 10-Qs in some years use a company-specific tag), the
most recent usable filing is used instead, as long as its period ended no more than
``max_age_days`` before the cut-off (400 by default: the last 10-K stays usable until the
next one is due).
"""
from __future__ import annotations

from functools import cache

import pandas as pd

from .config import SOURCES_DIR

FUNDAMENTALS_CSV = SOURCES_DIR / "sec_xbrl_fundamentals.csv"
REVENUE_PRIORITY = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
                    "SalesRevenueGoodsNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
                    "RevenuesNetOfInterestExpense", "SalesRevenueServicesNet"]
TOLERANCE_DAYS = 10


@cache
def load_facts() -> pd.DataFrame:
    df = pd.read_csv(FUNDAMENTALS_CSV, comment="#", parse_dates=["start", "end", "filed"])
    df["days"] = (df.end - df.start).dt.days
    return df


def _pick(facts: pd.DataFrame, start, end) -> float | None:
    near = ((facts.start - start).abs().dt.days <= TOLERANCE_DAYS) & ((facts.end - end).abs().dt.days <= TOLERANCE_DAYS)
    m = facts[near]
    return float(m.value.iloc[-1]) if len(m) else None


def _bank_revenue(f: pd.DataFrame) -> pd.DataFrame:
    """Net interest income + noninterest income for matching (start, end) periods."""
    nii = f[f.kind == "bank_net_interest_income"].set_index(["start", "end"]).value
    non = f[f.kind == "bank_noninterest_income"].set_index(["start", "end"]).value
    nii, non = nii[~nii.index.duplicated(keep="last")], non[~non.index.duplicated(keep="last")]
    both = (nii + non).dropna()
    if both.empty:
        return f.iloc[0:0]
    out = both.rename("value").reset_index()
    out["concept"], out["kind"] = "InterestIncomeExpenseNet+NoninterestIncome", "revenue"
    out["days"] = (out.end - out.start).dt.days
    out["form"], out["filed"] = f.form.iloc[0], f.filed.iloc[0]
    return out


def _from_filing(f: pd.DataFrame) -> dict | None:
    rev = f[f.kind == "revenue"]
    if rev.empty:
        rev = _bank_revenue(f)
    if rev.empty:
        return None
    end = rev.end.max()
    for concept in [*REVENUE_PRIORITY, "InterestIncomeExpenseNet+NoninterestIncome"]:
        c = rev[rev.concept == concept]
        cur = c[c.end == end]
        if cur.empty:
            continue
        cur = cur.loc[cur.days.idxmax()]
        start = cur.start
        prior = _pick(c, start - pd.DateOffset(years=1), end - pd.DateOffset(years=1))
        if not prior or prior <= 0:
            continue
        op, basis = _pick(f[f.kind == "operating_income"], start, end), "operating"
        if op is None:
            op, basis = _pick(f[f.kind == "pretax_income"], start, end), "pretax"
        if op is None:
            return None
        return {"period_start": start, "period_end": end, "form": cur.form, "filed": cur.filed,
                "revenue_concept": concept, "revenue": cur.value, "revenue_growth": cur.value / prior - 1,
                "margin": op / cur.value, "margin_basis": basis}
    return None


@cache
def snapshot(ticker: str, cutoff, max_age_days: int = 400) -> dict | None:
    """Latest usable fundamentals for ``ticker`` known on ``cutoff`` (filed <= cutoff)."""
    cutoff = pd.Timestamp(cutoff)
    facts = load_facts()
    facts = facts[(facts.ticker == ticker) & (facts.filed <= cutoff)]
    for accn in facts.sort_values(["filed", "end"], ascending=False).accn.unique():
        snap = _from_filing(facts[facts.accn == accn])
        if snap is not None:
            if (cutoff - snap["period_end"]).days > max_age_days:
                return None
            return {"ticker": ticker, **snap}
    return None


def rank_scores(tickers: list[str], cutoff, growth_weight: float = 0.5, margin_weight: float = 0.5,
                max_age_days: int = 400) -> pd.DataFrame:
    """Snapshot per ticker plus ranks (1 = best) on revenue growth and margin, and the weighted
    composite ``score = growth_weight * growth_rank + margin_weight * margin_rank`` (lower is
    better). Ties on score go to the larger company (earlier in ``tickers``, which is ordered
    by market cap). Tickers without a snapshot are returned with NaN scores."""
    df = pd.DataFrame([snapshot(t, pd.Timestamp(cutoff), max_age_days) or {"ticker": t} for t in tickers])
    df["cap_rank"] = range(1, len(df) + 1)
    df["growth_rank"] = df.get("revenue_growth").rank(ascending=False, method="min")
    df["margin_rank"] = df.get("margin").rank(ascending=False, method="min")
    df["score"] = growth_weight * df.growth_rank + margin_weight * df.margin_rank
    return df.sort_values(["score", "cap_rank"], na_position="last").reset_index(drop=True)

"""Phase 1: point-in-time "#1 S&P 500 company" table, one row per quarter start.

Each row's pick is observed at the *previous quarter-end close* (no lookahead):
the 1975-01-01 row reflects market caps on 1974-12-31.

Evidence per quarter-end (see data/sources/README.md for provenance):

  estimate  own market-cap estimate = nominal close x shares outstanding from
            filings / contemporaneous reports (1974-1995)          [sp500bt.mcap]
  cmc       companiesmarketcap.com history (1996+), rescaled to the exact
            quarter-end with Yahoo's price ratio
  ms        Morgan Stanley Counterpoint Global / FactSet year-end top-3 (1950-2023)
  dfa       Dimensional / CRSP start-of-decade top-10 (1969, 1979, ... 2019)
  ft        Financial Times Global 500 via Wikipedia: quarterly from 2006,
            one ~31-March snapshot per year 2000-2005
  press     Business Week 1000 / Forbes 500s market-value rankings (1985-1988)

Confidence rubric (applied per row, never averaged):
  HIGH    >= 2 independent sources name the same #1 and the quantitative margin
          over #2 is >= 2% (i.e. outside estimation noise)
  MEDIUM  the sources that exist agree but only one covers that exact date, or
          the margin is thin (< 2%), or share counts were extrapolated
  LOW     sources disagree, or a single estimate with a margin inside its error
          band (< 3% for own estimates, < 1% for vendor data); an ``alt_top1``
          is always given for LOW rows so the backtest can be re-run with it
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SOURCES_DIR
from .mcap import market_caps, nominal_price
from .prices import PriceDataError
from .universe import name_to_ticker

FIRST_QE, LAST_QE = "1974-12-31", "2025-12-31"
CMC_START = pd.Timestamp("1996-01-31")

# Candidate windows for the own-estimate era (dates are quarter-ends).
ESTIMATE_CANDIDATES = {
    "T_OLD": ("1974-12-31", "1983-12-31"),
    "IBM": ("1974-12-31", "1995-12-31"),
    "XOM": ("1974-12-31", "1995-12-31"),
    "GE": ("1983-12-31", "1995-12-31"),
    "WMT": ("1987-06-30", "1995-12-31"),
    "MO": ("1990-12-31", "1995-12-31"),
    "T_CORP": ("1991-03-31", "1996-09-30"),
    "KO": ("1993-03-31", "1995-12-31"),
}

SOURCE_URLS = {
    "estimate": "data/sources/share_counts.csv",
    "cmc": "https://companiesmarketcap.com/",
    "ms": "https://www.morganstanley.com/im/publication/insights/articles/article_stockmarketconcentration.pdf",
    "dfa": "https://www.spglobal.com/en/research-insights/market-insights/large-and-in-charge-giant-firms-atop-market-is-nothing-new",
    "ft": "https://en.wikipedia.org/w/index.php?title=List_of_public_corporations_by_market_capitalization&oldid=1371146339",
}


def quarter_ends() -> pd.DatetimeIndex:
    return pd.date_range(FIRST_QE, LAST_QE, freq="QE")


# ---------------------------------------------------------------- evidence builders
def estimate_ranking(qe: pd.DatetimeIndex) -> pd.DataFrame:
    m = market_caps(list(ESTIMATE_CANDIDATES), qe)
    keep = pd.Series(False, index=m.index)
    for t, (a, b) in ESTIMATE_CANDIDATES.items():
        keep |= (m.ticker == t) & (m.date >= a) & (m.date <= b)
    m = m[keep].copy()
    m["source"] = "estimate"
    return m[["date", "ticker", "mcap_bn", "source", "shares_extrapolated", "price_date"]]


def cmc_ranking(qe: pd.DatetimeIndex, max_gap_days: int = 40) -> pd.DataFrame:
    """companiesmarketcap values at each quarter-end, rescaled from the nearest
    observation on or before the quarter-end by the nominal price ratio."""
    h = pd.read_csv(SOURCES_DIR / "companiesmarketcap_history.csv", parse_dates=["date"])
    rows = []
    for t, g in h.groupby("ticker"):
        s = g.set_index("date")["mcap_usd"].sort_index()
        try:
            px = nominal_price(t)
        except PriceDataError:
            px = None
        for d in qe[qe >= CMC_START - pd.Timedelta(days=31)]:
            sub = s.loc[:d]
            if sub.empty or (d - sub.index[-1]).days > max_gap_days:
                continue
            obs_d, val = sub.index[-1], float(sub.iloc[-1])
            scale = 1.0
            if px is not None and obs_d != d:
                p0, p1 = px.loc[:obs_d], px.loc[:d]
                if len(p0) and len(p1):
                    scale = float(p1.iloc[-1] / p0.iloc[-1])
            rows.append({"date": d, "ticker": t, "mcap_bn": val * scale / 1e9, "source": "cmc",
                         "obs_date": obs_d, "shares_extrapolated": False})
    return pd.DataFrame(rows)


def google_pre_cmc(qe: pd.DatetimeIndex) -> pd.DataFrame:
    """Google 2004-09..2013-12: companiesmarketcap's Alphabet series starts 2014-03,
    so compute nominal close x (class A + class B) from 10-K/10-Q covers."""
    q = qe[(qe >= "2005-03-31") & (qe <= "2013-12-31")]
    m = market_caps(["GOOGL"], q)
    m["source"] = "estimate"
    return m[["date", "ticker", "mcap_bn", "source", "shares_extrapolated", "price_date"]]


def ms_yearend() -> pd.DataFrame:
    df = pd.read_csv(SOURCES_DIR / "ms_counterpoint_exhibit2_yearend_top3.csv", comment="#")
    df["date"] = pd.to_datetime(df.year_end.astype(str) + "-12-31")
    return df


def dfa_decades() -> pd.DataFrame:
    df = pd.read_csv(SOURCES_DIR / "dimensional_decade_top10.csv", comment="#")
    df["date"] = pd.to_datetime(df.year_end.astype(str) + "-12-31")
    return df


def _ft_ticker(name: str, date: pd.Timestamp, uni: pd.DataFrame) -> str | None:
    if name.strip() == "AT&T":
        if date < pd.Timestamp("1984-01-01"):
            return "T_OLD"
        return "T_CORP" if date < pd.Timestamp("2005-11-18") else "T"
    return name_to_ticker(name, uni)


def ft_ranking(uni: pd.DataFrame) -> pd.DataFrame:
    """US constituents of the FT/Wikipedia top-10 lists, keyed by as-of date.
    2000-2005 tables are single snapshots as of ~31 March of the labelled year
    (Wikipedia labels 2002/2003 'December' but the figures match March prices)."""
    ft = pd.read_csv(SOURCES_DIR / "wikipedia_ft_global_top10.csv")
    qmap = {"Q1": "03-31", "Q2": "06-30", "Q3": "09-30", "Q4": "12-31", "annual": "03-31"}
    ft["date"] = pd.to_datetime(ft.year.astype(str) + "-" + ft.period.map(qmap))
    errata = pd.read_csv(SOURCES_DIR / "source_errata.csv")
    errata = errata[errata.source == "wikipedia_ft_global_top10"]
    ft["erratum"] = ""
    for e in errata.itertuples():
        hit = (ft.year == e.year) & (ft.period == e.period) & (ft["rank"] == e.rank) & (ft.company == e.wrong_company)
        ft.loc[hit, "company"] = e.corrected_company
        ft.loc[hit, "erratum"] = f"label corrected from {e.wrong_company} (data/sources/source_errata.csv)"
    ft["ticker"] = [_ft_ticker(n, d, uni) for n, d in zip(ft.company, ft.date, strict=True)]
    return ft


def press_snapshots() -> pd.DataFrame:
    s = pd.read_csv(SOURCES_DIR / "market_value_snapshots.csv", parse_dates=["as_of"])
    return s[s["rank"].notna()]


# ---------------------------------------------------------------- decision
def _votes_at(d: pd.Timestamp, ms, dfa, ft, press) -> list[tuple[str, str, str]]:
    """(source, #1 ticker, url) for every anchor source that observed date d."""
    votes = []
    for name, df in (("ms", ms), ("dfa", dfa)):
        r = df[(df.date == d) & (df["rank"] == 1)]
        if len(r):
            votes.append((name, r.iloc[0].ticker, SOURCE_URLS[name]))
    f = ft[(ft.date == d) & ft.ticker.notna()].sort_values("rank")
    if len(f):
        top = f.iloc[0]
        # FT lists are global: the top US name is the S&P #1 only if every
        # higher-ranked name is non-US (ticker is None), which holds by construction
        url = top.ref_url if isinstance(top.ref_url, str) and top.ref_url else SOURCE_URLS["ft"]
        votes.append(("ft", top.ticker, url))
    p = press[(press.as_of - d).abs() <= pd.Timedelta(days=21)]
    if len(p):
        p = p.sort_values("rank")
        votes.append(("press:" + p.iloc[0].publication, p.iloc[0].ticker, p.iloc[0].source_url))
    return votes


def decide(ranking: pd.DataFrame, ms, dfa, ft, press, uni) -> pd.DataFrame:
    out = []
    prev_top = None
    names = dict(zip(uni.ticker, uni.name, strict=True))
    for d, g in ranking.groupby("date"):
        g = g.sort_values("mcap_bn", ascending=False).reset_index(drop=True)
        est_src = g.source.iloc[0]
        lead, second = g.iloc[0], g.iloc[1]
        margin = lead.mcap_bn / second.mcap_bn - 1
        extrap = bool(g.head(2).shares_extrapolated.any())
        noise = 0.03 if est_src == "estimate" else 0.01
        votes = _votes_at(d, ms, dfa, ft, press)
        anchor_tops = {v[1] for v in votes}
        quant_pick = lead.ticker
        tie = margin < min(noise, 0.01)
        kept_incumbent = tie and prev_top == second.ticker
        if kept_incumbent:
            quant_pick = prev_top  # dead heat: keep the incumbent rather than flip on noise
        notes = []
        if not votes:
            top = quant_pick
            if margin < noise or tie:
                conf = "LOW"
            else:
                conf = "MEDIUM"
            alt = second.ticker if top == lead.ticker else lead.ticker
            if kept_incumbent:
                notes.append(f"dead heat ({margin:.2%}); incumbent {prev_top} kept")
            elif tie:
                notes.append(f"dead heat ({margin:.2%}) between {lead.ticker} and {second.ticker}")
        elif anchor_tops == {lead.ticker}:
            top = lead.ticker
            conf = "HIGH" if margin >= 0.02 and not extrap else "MEDIUM"
            alt = second.ticker
        elif len(anchor_tops) == 1:
            # anchors agree with each other but not with the quantitative ranking
            top = next(iter(anchor_tops))
            conf = "LOW"
            alt = lead.ticker
            notes.append(f"{est_src} ranks {lead.ticker} first by {margin:.1%}; "
                         f"{'/'.join(v[0] for v in votes)} say {top}")
        else:
            # anchors disagree among themselves -> majority incl. quantitative vote
            tally = pd.Series([v[1] for v in votes] + [lead.ticker]).value_counts()
            top = tally.index[0]
            conf = "LOW"
            alt = tally.index[1] if len(tally) > 1 else second.ticker
            notes.append("sources disagree: " + ", ".join(f"{v[0]}={v[1]}" for v in votes))
        if extrap and conf == "HIGH":
            conf = "MEDIUM"
        if extrap:
            notes.append("share count extrapolated beyond nearest filing")
        run = g[g.ticker != top].iloc[0]
        top_cap = float(g.loc[g.ticker == top, "mcap_bn"].iloc[0]) if (g.ticker == top).any() else np.nan
        urls = [SOURCE_URLS[est_src]] + [v[2] for v in votes]
        out.append({
            "observation_date": d.date(), "date": (d + pd.Timedelta(days=1)).date(),
            "top1_ticker": top, "top1_company_name": names.get(top, top),
            "confidence": conf, "alt_top1_ticker": alt if conf == "LOW" else "",
            "top1_mcap_bn": round(top_cap, 1), "runner_up_ticker": run.ticker,
            "runner_up_mcap_bn": round(float(run.mcap_bn), 1),
            "margin_pct": round((top_cap / run.mcap_bn - 1) * 100, 1),
            "quant_source": est_src,
            "anchors": "; ".join(f"{v[0]}={v[1]}" for v in votes),
            "source_url": " | ".join(dict.fromkeys(u for u in urls if isinstance(u, str) and u)),
            "notes": "; ".join(notes),
        })
        prev_top = top
    return pd.DataFrame(out)


def top10_lists(ranking: pd.DataFrame, uni: pd.DataFrame) -> pd.DataFrame:
    """S&P 500 members only, by the quantitative ranking at each quarter-end."""
    added = dict(zip(uni.ticker, uni.sp500_added, strict=True))
    rows = []
    for d, g in ranking[ranking.source == "cmc"].groupby("date"):
        g = g[[added.get(t, pd.Timestamp.max) <= d for t in g.ticker]]
        g = g.sort_values("mcap_bn", ascending=False).head(10)
        rows.append({"observation_date": d.date(), "top10": ",".join(g.ticker)})
    return pd.DataFrame(rows)

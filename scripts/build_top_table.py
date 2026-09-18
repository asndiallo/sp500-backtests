"""Build data/largest_company_by_quarter.csv and data/top1_transitions.csv (Phase 1).

Run:  python scripts/build_top_table.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sp500bt import phase1  # noqa: E402
from sp500bt.config import (  # noqa: E402
    DATA_DIR,
    MANUAL_PRICES_DIR,  # noqa: E402
    SOURCES_DIR,
    TOP20_CSV,
    TOP_HOLDINGS_CSV,
)
from sp500bt.mcap import manual_nominal  # noqa: E402
from sp500bt.prices import load_yahoo_history  # noqa: E402
from sp500bt.universe import load_universe  # noqa: E402

TRANSITIONS_CSV = DATA_DIR / "top1_transitions.csv"
CONTEXT_CSV = SOURCES_DIR / "transition_context.csv"
TOP10_COMPLETE_FROM = pd.Timestamp("2006-03-31")  # before this, delisted mega-caps are missing
# Top-20: Wachovia (absorbed 2008-12-31) and Genentech (bought out 2009-03-26) have no price or
# market-cap history here and sat near rank 20 until then; from the 2009-03-31 observation every
# plausible top-20 member is a survivor in data/universe.csv.
TOP20_COMPLETE_FROM = pd.Timestamp("2009-03-31")


def build_ranking(qe: pd.DatetimeIndex, uni: pd.DataFrame) -> pd.DataFrame:
    est = phase1.estimate_ranking(qe[qe < phase1.CMC_START])
    t_corp_1996 = phase1.estimate_ranking(pd.DatetimeIndex(["1996-03-31", "1996-06-30", "1996-09-30"]))
    goog = phase1.google_pre_cmc(qe)
    cmc = phase1.cmc_ranking(qe)
    cmc = cmc[cmc.date >= phase1.CMC_START]
    ranking = pd.concat([est, cmc, t_corp_1996[t_corp_1996.ticker == "T_CORP"], goog], ignore_index=True)
    added = dict(zip(uni.ticker, uni.sp500_added, strict=True))
    in_index = [added.get(t, pd.Timestamp.min) <= d for t, d in zip(ranking.ticker, ranking.date, strict=True)]
    return ranking[in_index]


# Structural caveats: #1 spells that reflect a corporate event rather than organic strength.
STRUCTURAL = [
    ("T_OLD", "1982-01-08", "1983-12-31",
     "pre-breakup Bell System: divestiture agreed 1982-01-08, effective 1984-01-01"),
    ("T_CORP", "1994-09-19", "1994-12-31", "acquisition-inflated: McCaw Cellular stock deal closed Sep 1994"),
    ("XOM", "1999-11-30", "2099-12-31", "merged entity: Exxon + Mobil (1999-11-30)"),
]


def _ret(t: str, a: pd.Timestamp, b: pd.Timestamp) -> float:
    """Split-adjusted price return (what moves market cap; dividends excluded)."""
    px = manual_nominal(t) if (MANUAL_PRICES_DIR / f"{t}.csv").exists() else load_yahoo_history(t)["Close"]
    return float(px.loc[:b].iloc[-1] / px.loc[:a].iloc[-1] - 1)


def transitions(table: pd.DataFrame, ranking: pd.DataFrame) -> pd.DataFrame:
    ctx = pd.read_csv(CONTEXT_CSV, parse_dates=["date"]) if CONTEXT_CSV.exists() else pd.DataFrame()
    rows = []
    prev = None
    for r in table.itertuples():
        if prev is not None and r.top1_ticker != prev.top1_ticker:
            a, b = pd.Timestamp(prev.observation_date), pd.Timestamp(r.observation_date)
            try:
                ra, rb = _ret(r.top1_ticker, a, b), _ret(prev.top1_ticker, a, b)
                why = (f"{r.top1_ticker} price {ra:+.0%} vs {prev.top1_ticker} {rb:+.0%} over "
                       f"{a.date()}..{b.date()}")
            except Exception as e:  # noqa: BLE001 -- surfaced in the reason text
                why = f"relative move unavailable ({e})"
            c = ctx[(ctx.date > a) & (ctx.date <= b) & (ctx.kind != "structural")] if len(ctx) else ctx
            context = " | ".join(c.context) if len(c) else ""
            srcs = " | ".join(c.source_url) if len(c) else ""
            rows.append({"effective_date": r.date, "observed_at": r.observation_date,
                         "from_ticker": prev.top1_ticker, "to_ticker": r.top1_ticker,
                         "confidence": r.confidence, "reason": why + (f"; {context}" if context else ""),
                         "context_source_url": srcs, "row_type": "quarter_transition"})
        prev = r
    for c in ctx.itertuples():  # documented exact-date events (intraday/close flips, structural events)
        rows.append({"effective_date": c.date.date(), "observed_at": c.date.date(), "from_ticker": "",
                     "to_ticker": "", "confidence": "HIGH (dated news source)", "reason": c.context,
                     "context_source_url": c.source_url, "row_type": f"documented_event:{c.kind}"})
    return pd.DataFrame(rows).sort_values(["effective_date", "row_type"]).reset_index(drop=True)


def main() -> None:
    uni = load_universe()
    qe = phase1.quarter_ends()
    ranking = build_ranking(qe, uni)
    ranking.to_csv(SOURCES_DIR / "derived_quarter_end_market_caps.csv", index=False)
    ms, dfa, press = phase1.ms_yearend(), phase1.dfa_decades(), phase1.press_snapshots()
    ft = phase1.ft_ranking(uni)
    unmapped = sorted(set(ft[ft.ticker.isna()].company))
    print(f"FT names without a US ticker mapping (should all be non-US): {unmapped}")

    table = phase1.decide(ranking, ms, dfa, ft, press, uni)
    t10 = phase1.top10_lists(ranking, uni)
    table = table.merge(t10, on="observation_date", how="left")
    obs = pd.to_datetime(table.observation_date)
    table["top10_status"] = ["COMPLETE" if d >= TOP10_COMPLETE_FROM
                             else ("PARTIAL" if isinstance(t, str) else "UNRESOLVED")
                             for d, t in zip(obs, table.top10, strict=True)]
    pairs = list(zip(table.top10, table.top10_status, strict=True))
    table["top10_tickers"] = [t if s == "COMPLETE" else "UNRESOLVED" for t, s in pairs]
    table["top10_partial_candidates"] = [t if s == "PARTIAL" else "" for t, s in pairs]

    tr = transitions(table, ranking)
    qt = tr[tr.row_type == "quarter_transition"]
    table["transition_reason"] = table.date.map(dict(zip(qt.effective_date, qt.reason, strict=True))).fillna("")
    d = pd.to_datetime(table.date)
    table["structural_flag"] = ""
    for t, a, b, text in STRUCTURAL:
        hit = (table.top1_ticker == t) & (d > pd.Timestamp(a)) & (d <= pd.Timestamp(b) + pd.Timedelta(days=1))
        table.loc[hit, "structural_flag"] = text
    cols = ["date", "top1_ticker", "top1_company_name", "top10_tickers", "source_url", "confidence",
            "observation_date", "alt_top1_ticker", "top1_mcap_bn", "runner_up_ticker", "runner_up_mcap_bn",
            "margin_pct", "quant_source", "anchors", "top10_status", "top10_partial_candidates",
            "transition_reason", "structural_flag", "notes"]
    table[cols].to_csv(TOP_HOLDINGS_CSV, index=False)
    tr.to_csv(TRANSITIONS_CSV, index=False)
    write_top20(table, ranking, uni)
    print(table.confidence.value_counts().to_dict())
    print(table.groupby(pd.to_datetime(table.date).dt.year // 10 * 10).confidence.value_counts().unstack(fill_value=0))
    print(f"wrote {TOP_HOLDINGS_CSV} ({len(table)} rows) and {TRANSITIONS_CSV} ({len(tr)} transitions)")


def write_top20(table: pd.DataFrame, ranking: pd.DataFrame, uni: pd.DataFrame) -> None:
    """data/top20_by_quarter.csv, keyed like the Phase 1 table. Lists are published only from
    TOP20_COMPLETE_FROM; ranks 1-10 must equal the Phase 1 COMPLETE top-10 list."""
    t20 = phase1.topn_lists(ranking, uni, 20, detail=True)
    out = table[["date", "observation_date", "top10_tickers", "top10_status"]].merge(t20, on="observation_date",
                                                                                    how="left")
    obs = pd.to_datetime(out.observation_date)
    out["top20_status"] = ["COMPLETE" if d >= TOP20_COMPLETE_FROM else "UNRESOLVED" for d in obs]
    out["top20_tickers"] = [t if s == "COMPLETE" else "UNRESOLVED" for t, s in zip(out.top20, out.top20_status,
                                                                                 strict=True)]
    done = out.top20_status == "COMPLETE"
    first10 = out.top20.str.split(",").str[:10].str.join(",")
    bad = out[done & (out.top10_status == "COMPLETE") & (first10 != out.top10_tickers)]
    if len(bad):
        raise AssertionError(f"top-20 ranks 1-10 disagree with the Phase 1 top-10 on {list(bad.date)}")
    cols = ["date", "observation_date", "top20_tickers", "top20_status", "rank20_mcap_bn", "rank21_ticker",
            "rank21_mcap_bn", "members_ranked"]
    out.loc[~done, ["rank20_mcap_bn", "rank21_ticker", "rank21_mcap_bn"]] = None
    out[cols].to_csv(TOP20_CSV, index=False)
    print(f"wrote {TOP20_CSV} ({int(done.sum())} COMPLETE quarters)")


if __name__ == "__main__":
    main()

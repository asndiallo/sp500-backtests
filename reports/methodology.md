# Methodology, data corrections and known gaps

[← index](../REPORT.md) · sources: [`data/sources/README.md`](../data/sources/README.md)

## Phase 1 table vs the original starter table

The starter 2011–2026 table had several errors that the sourced table corrects:

- **2019-01-01:** Microsoft, not Apple. MSFT closed 2018 at $780B vs AAPL $746B; Morgan Stanley and FT agree.
- **2024-01-01:** Apple, not Microsoft ($2.99T vs $2.79T at the 2023 close).
- **2024-06-01 "NVDA":** Nvidia's close above Microsoft on 2024-06-18 was reversed before the quarter ended. The 2024-07-01 row is Microsoft, and Nvidia's first quarter-end #1 is 2025-06-30.
- **Missing flips:** the table now also captures Exxon/Apple trading places in 2011–2013 (Apple at 2011-09-30, Exxon at 2011-12-31 and 2013-06-30) and Microsoft at 2020-03-31.

## Known gaps and data caveats (logged, not hidden)

- **No Stooq fallback.** pandas-datareader 0.11 removed its Stooq reader, and stooq.com now puts downloads behind a JavaScript proof-of-work bot check, which I did not circumvent. In its place, the one family Yahoo lacks (old AT&T and AT&T Corp) is hand-built from sourced data. All 71 Yahoo series fetched cleanly (`results/data_quality/price_fetch_report.csv`).
- **Old AT&T prices are month-end high–low averages** of the last trading day, not closes (±0.5%). AT&T Corp's **1998 month-ends are log-interpolated** between dividend-date prices because the source table skips 1998.
- **Top-10 lists:** UNRESOLVED for 1975–1995 (no source for full lists), PARTIAL for 1996–2005 (companiesmarketcap lacks delisted giants such as AT&T Corp, Lucent, AOL/Time Warner and BellSouth, so lists there are survivorship-biased), COMPLETE from 2006. The top-10 variant therefore runs 2006–2026 only.
- **Correction (2026-09-18): Google was missing from the 2008–2014 top-10 lists.**
  - **Cause.** companiesmarketcap's Alphabet series starts in 2014-03, so Google's 2006–2013 market caps are my own estimates from its 10-K/10-Q share counts. The #1 decision always used them, but the top-10 list builder read only vendor rows.
  - **Effect.** Google was dropped from 19 "COMPLETE" lists (2008-01-01 → 2014-01-01), where it actually ranked #3–#10. The marginal #10 name held its place instead.
  - **Fix.** `phase1.topn_lists` now ranks estimate rows alongside vendor rows from 1996 on. This also adds AT&T Corp to the 1996 PARTIAL candidate lists.
  - **Unaffected:** #1, runner-up and every top1 result.
  - **Re-run families:** `top10_ew`, `random_pick_placebo`, `alt_pickers` (ranks 2–5) and `fundamentals_picker` (references).

  | Run                                           | Before |  After |
  | --------------------------------------------- | -----: | -----: |
  | Top-10 equal-weight, 2006–2026, XIRR          | 14.67% | 15.00% |
  | Top-10 equal-weight, 2006–2026, Sharpe        |   0.72 |   0.73 |
  | Top-10 equal-weight, 2006–2026, trailing stop | 12.80% | 13.04% |
  | Ranks 2–5 equal-weight                        | 16.58% | 16.89% |
  | 2012–2026 top-10 equal-weight reference       | 17.77% | 18.39% |

  No conclusion changed. The placebo numbers in its report are the corrected ones.

- **Top-20 lists** (`data/top20_by_quarter.csv`, Phase 7). COMPLETE from the 2009-03-31 observation only: Wachovia (absorbed 2008-12-31) and Genentech (bought out 2009-03-26) sat near rank 20 before then, and neither has price or market-cap history here.
  - 27 surviving S&P 500 names that could plausibly reach rank 20 were added to `data/universe.csv` (companiesmarketcap history fetched for them only, via `fetch_sources.py cmc_missing`).
  - Only PayPal (2020–21) actually entered a top-20 list.
  - Ranks 1–10 of every top-20 list equal the corrected top-10 list; the build asserts this.
- **IBM's 1974–75 share counts are extrapolated.** The 1975-01-01 row (AT&T by Morgan Stanley; IBM by my estimate, 0.8% apart) is LOW for that reason.
- **Third-party source errors I found and corrected or excluded:**
  - Wikipedia's 2024 Q2/Q3 Apple/Microsoft labels are transposed.
  - Wikipedia's 2002/2003 FT tables are March data labelled "December".
  - finhacker.cz's survivorship-biased S&P list was rejected.
  - My own first read of the Morgan Stanley exhibit had one row mislabeled (P&G read as "Intel"); fixed.
- **The index leg before 1988** is ^GSPC plus Shiller dividends. Over 1988–2023 that method trails ^SP500TR by 0.06%/yr (daily correlation 0.9996), and its calendar-year returns match published S&P 500 totals within 0.5 pp.
- **Price sanity checks** (`scripts/check_prices.py`): every symbol that was ever a #1 pick matches at least one independent dated print (UPI, Washington Post, NBC, CNBC, Seattle Times, SEC filings, Wollman), all within 2%. Every universe ticker's price is also cross-checked against companiesmarketcap's market cap.

# Fundamentals picker: revenue growth + margin among the top 10

[← index](../REPORT.md) · config: [`scenarios/fundamentals_picker.toml`](../scenarios/fundamentals_picker.toml) · results: [`results/fundamentals_picker/`](../results/fundamentals_picker/) (`fundamental_scores.csv` has every quarter's ranking)

**Question.** Instead of the biggest company, buy the top-10 member with the best recent business momentum. Does that beat size alone?

**Data: SEC XBRL filings, point-in-time.** `python scripts/fetch_sources.py sec` stores every us-gaap USD duration fact for the 30 companies that appear in a complete top-10 list, from the SEC companyfacts API (public domain) → `data/sources/sec_xbrl_fundamentals.csv`. Each company's CIK is checked against SEC's own name in `data/sources/sec_ciks.csv`. `sp500bt/fundamentals.py` builds one snapshot per company per quarter:

- **Cut-off.** Only filings **filed on or before** the row's quarter-end observation date are used, so there is no look-ahead. Restatements filed later never leak backwards.
- **Revenue growth.** From the most recent usable 10-K/10-Q: fiscal year-to-date revenue ÷ the prior-year year-to-date comparative **in the same filing** − 1. No seasonality, and no mixing of original and restated numbers. Revenue is the first standard revenue tag present; banks that tag no total revenue use net interest income + noninterest income.
- **Margin.** Year-to-date operating income ÷ revenue. Banks, insurers and Berkshire report no operating income, so they use **pre-tax income** (221 of 649 snapshots).
- **Staleness.** A snapshot must come from a period ending no more than 400 days before the cut-off (`max_age_days`), which keeps the last 10-K usable until the next is due. The median snapshot is 93 days old.
- **Score.** `score = growth_weight × growth rank + margin_weight × margin rank` among that quarter's top 10 (rank 1 = best; weights 50/50; ties go to the larger company). The best score gets the $500. Growth-only (100/0) and margin-only (0/100) are sensitivities.

**Window: 2012-04-01 → 2026-01-02 (56 quarters).**

- XBRL starts in 2009–10, but Exxon's early filings carry revenue only under a company-specific tag, so no usable Exxon snapshot exists until 2012. Exxon was the #1 for most of that time, so dropping it would bias the universe.
- 2012-04-01 is the first quarter where **all ten** members have data. The picker raises if any member is missing (`min_coverage = 10`), so the universe never silently shrinks.
- The #1 and top-10 equal-weight are re-run over the same window as references. This window is dominated by mega-cap tech: the index leg earned 14.74%.

| Picker | Rule | Window | Switches | Distinct names | Stock-leg final | XIRR | Sharpe | Sortino | Max DD | Index XIRR | Index Sharpe |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| #1 (reference) | Baseline hold | 2012–2026 | 9 | 4 | $183,212 | 24.57% | 0.80 | 1.35 | −44% | 14.74% | 0.92 |
| #1 (reference) | Trailing stop 25% | 2012–2026 | 9 | 4 | $90,607 | 15.74% | 0.65 | 1.01 | −41% | 14.74% | 0.92 |
| #1 (reference) | Buy the dip | 2012–2026 | 9 | 4 | $316,661 | 26.28% | 0.81 | 1.38 | −44% | 14.74% | 0.92 |
| Top-10 equal-weight | Baseline hold | 2012–2026 | 32 | 24 | $111,805 | 18.39% | 1.03 | 1.70 | −30% | 14.74% | 0.92 |
| Growth + margin rank (50/50) | Baseline hold | 2012–2026 | 11 | 6 | $171,544 | 23.75% | 0.88 | 1.47 | −44% | 14.74% | 0.92 |
| Growth + margin rank (50/50) | Trailing stop 25% | 2012–2026 | 11 | 6 | $105,605 | 17.68% | 0.79 | 1.26 | −41% | 14.74% | 0.92 |
| Growth + margin rank (50/50) | Buy the dip | 2012–2026 | 11 | 6 | $317,838 | 25.85% | 0.88 | 1.48 | −44% | 14.74% | 0.92 |
| Growth rank only | Baseline hold | 2012–2026 | 9 | 8 | $155,834 | 22.55% | 0.83 | 1.37 | −49% | 14.74% | 0.92 |
| Margin rank only | Baseline hold | 2012–2026 | 10 | 8 | $106,072 | 17.73% | 0.81 | 1.30 | −33% | 14.74% | 0.92 |

## What this says

**Picks.** The 50/50 score picked:

| Company   | Quarters | When             |
| --------- | -------: | ---------------- |
| Meta      |       20 | 2015–2022        |
| Apple     |       10 | 2012–13, 2015–16 |
| Nvidia    |       10 | 2023–26          |
| Microsoft |        8 | 2014–15, 2020–21 |
| Visa      |        7 | 2019, 2022–23    |
| Berkshire |        1 |                  |

It picked the same name as the #1 in only 12 of 56 quarters (21%) and switched 11 times (the #1 switched 9 times).

**Return: close to the #1, not better.**

- 23.75% XIRR vs 24.57% for the #1 on baseline hold, and 25.85% vs 26.28% with buy-the-dip.
- Both are far above top-10 equal-weight (18.39%) and the index (14.74%). Over 2012–2026, _any_ rule that concentrated in the fastest-growing mega-caps did well.

**Risk: somewhat better than the #1, still below equal-weight.**

- Sharpe 0.88 vs 0.80 for the #1, with the same −44% worst drawdown: Apple's 2012-09 → 2013-04 slide, which both hit because both bought Apple first.
- Top-10 equal-weight had the best risk-adjusted result (Sharpe 1.03, drawdown −30%). The index was 0.92.

**Which factor matters.** Growth alone (22.55%) carries most of the result. Margin alone (17.73%) slightly trails equal-weight (18.39%). The highest margins belonged to Visa (21 quarters) and Wells Fargo (11 quarters, on the pre-tax basis) rather than the decade's biggest winners. The trailing stop hurts here, as in every mega-cap-tech window (17.68%).

**Caveats.**

- **Berkshire's pre-tax "margin" is inflated.** Since 2018, unrealized investment gains run through income, which put its pre-tax margin at 74% in mid-2023. That won the 2023-07-01 pick. It is one quarter of 56, and it is left as-is rather than hand-patched.
- **One 14-year window.** It is favourable to growth, so this is not evidence that fundamentals-based picking works in general.
- **Verdict.** A defensible growth + margin screen matched the #1 on return with a modestly better Sharpe. It did not beat the #1 on return, and equal-weighting the same ten names had the best risk-adjusted outcome.

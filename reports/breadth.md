# Breadth: #1 vs top-3, top-10 and top-20 equal-weight

[← index](../REPORT.md) · config: [`scenarios/breadth.toml`](../scenarios/breadth.toml) · results: [`results/breadth/`](../results/breadth/) · lists: [`data/top20_by_quarter.csv`](../data/top20_by_quarter.csv)

**Question.** How much of the #1 strategy's result, and its risk, comes from holding one name? Split the same $500/quarter equally across the n largest S&P 500 members (`topn_ew`, n = 1, 3, 10, 20). Rules, index leg and valuation are as everywhere else.

**Complete-data windows only.**

- **Top-3** uses the Phase 1 top-10 lists: COMPLETE from 2006-04-01, the same window as [top10_ew](top10_ew.md).
- **Top-20** needs ranks 11–20, which the Phase 1 table doesn't carry. `data/top20_by_quarter.csv` is built by `scripts/build_top_table.py` from the same quarter-end ranking as the top-10 lists, after adding 27 surviving S&P 500 names that could plausibly reach rank 20 to `data/universe.csv`.
  - It is COMPLETE from **2009-04-01**. Before that, Wachovia and Genentech (both near rank 20 until their 2008–09 takeovers) have no data.
  - Ranks 1–10 always equal the top-10 list (asserted by the build).
- The picker refuses any quarter whose list is not COMPLETE. The top-20 build also surfaced a bug in the top-10 lists (Google missing in 2008–2014), fixed before these runs ([methodology](methodology.md)).

Risk columns: monthly Sharpe/Sortino vs 3-month T-bills, daily max drawdown of the stock leg's unit value ([definitions](risk_metrics.md)). "Switches" counts quarters in which the set of names receiving money changed.

## The ladder on a common window (2009-04-01 → 2026-01-02, baseline hold)

| Picker    | Rule          | Window    | Switches | Distinct names | Stock-leg final |   XIRR | Sharpe | Sortino | Max DD | Index XIRR | Index Sharpe |
| --------- | ------------- | --------- | -------: | -------------: | --------------: | -----: | -----: | ------: | -----: | ---------: | -----------: |
| #1        | Baseline hold | 2009–2026 |       12 |              4 |        $212,320 | 19.33% |   0.79 |    1.35 |   −34% |     14.71% |         1.01 |
| Top-3 EW  | Baseline hold | 2009–2026 |       14 |              9 |        $256,227 | 21.17% |   1.06 |    1.88 |   −29% |     14.71% |         1.01 |
| Top-10 EW | Baseline hold | 2009–2026 |       44 |             24 |        $178,098 | 17.59% |   1.10 |    1.86 |   −29% |     14.71% |         1.01 |
| Top-20 EW | Baseline hold | 2009–2026 |       57 |             45 |        $145,296 | 15.56% |   1.03 |    1.71 |   −30% |     14.71% |         1.01 |

## Top-3 equal-weight, 2006–2026, three rules

For comparison over the same window ([top10_ew](top10_ew.md)): #1 15.53% (Sharpe 0.67), top-10 equal-weight 15.00% (0.73), index 13.41% (0.66).

| Picker   | Rule              | Window    | Switches | Distinct names | Stock-leg final |   XIRR | Sharpe | Sortino | Max DD | Index XIRR | Index Sharpe |
| -------- | ----------------- | --------- | -------: | -------------: | --------------: | -----: | -----: | ------: | -----: | ---------: | -----------: |
| Top-3 EW | Baseline hold     | 2006–2026 |       18 |             12 |        $308,390 | 17.89% |   0.76 |    1.21 |   −57% |     13.41% |         0.66 |
| Top-3 EW | Trailing stop 25% | 2006–2026 |       18 |             12 |        $211,313 | 14.81% |   0.72 |    1.12 |   −51% |     13.41% |         0.66 |
| Top-3 EW | Buy the dip       | 2006–2026 |       18 |             12 |        $551,353 | 18.39% |   0.72 |    1.13 |   −64% |     13.41% |         0.66 |

## Top-20 equal-weight, 2009–2026, three rules

| Picker    | Rule              | Window    | Switches | Distinct names | Stock-leg final |   XIRR | Sharpe | Sortino | Max DD | Index XIRR | Index Sharpe |
| --------- | ----------------- | --------- | -------: | -------------: | --------------: | -----: | -----: | ------: | -----: | ---------: | -----------: |
| Top-20 EW | Baseline hold     | 2009–2026 |       57 |             45 |        $145,296 | 15.56% |   1.03 |    1.71 |   −30% |     14.71% |         1.01 |
| Top-20 EW | Trailing stop 25% | 2009–2026 |       57 |             45 |        $118,120 | 13.48% |   0.97 |    1.57 |   −31% |     14.71% |         1.01 |
| Top-20 EW | Buy the dip       | 2009–2026 |       57 |             45 |        $253,184 | 17.35% |   1.04 |    1.73 |   −32% |     14.71% |         1.01 |

## What this says

**Returns peak at three names; risk-adjusted returns plateau from about three names.**

- **XIRR** runs #1 19.33% → top-3 21.17% → top-10 17.59% → top-20 15.56%, against the index's 14.71%.
- **Sharpe** jumps from 0.79 for the #1 to 1.06 for the top-3, then stays near 1.03–1.10 for 10 and 20 names, level with the index (1.01).
- **Max drawdown** falls from −34% (#1) to about −30% for every basket.
- **Reading.** Adding the #2 and #3 removed most of the single-stock risk without diluting the mega-cap exposure that drove this window. Going to 10 or 20 names mostly converges on the index.

**Top-3 is the most favourable breadth in both windows, but it is the same regime bet.**

- **2006–2026:** 17.89% vs 15.53% for the #1, with a Sharpe of 0.76 vs 0.67.
- **Caveat:** these windows (2006+, 2009+) are exactly the era in which the largest names kept winning (see the [placebo](random_pick_placebo.md)). There are no complete top-3 lists before 2006 to test the 1975–2005 era, when the #1 lagged badly and the #2 did better ([alt pickers](alt_pickers.md)).

**Rules behave as for the #1.** The trailing stop costs 2–3 pp in every basket in these mega-cap-led windows (the stop sells leaders on dips that later recover). Buy-the-dip adds 0.5–2 pp of XIRR on more capital, with a lower or equal Sharpe.

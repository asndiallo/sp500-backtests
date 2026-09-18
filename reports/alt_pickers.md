# Alternative pickers: margin buffer, the #2, ranks 2–5

[← index](../REPORT.md) · config: [`scenarios/alt_pickers.toml`](../scenarios/alt_pickers.toml) · results: [`results/alt_pickers/`](../results/alt_pickers/) (`runs.csv`, `risk.csv`, `pick_switches.csv`)

**Question.** Is "buy the #1" the right way to express "buy the biggest companies"? Three variations on who gets the quarterly $500. Everything else (both legs, the rules, valuation on 2026-01-02) is the top1_core framework.

**Pickers (parameters in the config).**

- **Margin buffer** (`top1_margin_buffer`, `buffer = 0.05`; 10% and 20% as sensitivities). New money keeps going to the incumbent #1 until a challenger's market cap exceeds the incumbent's by more than the buffer at the quarter-end observation.
  - Caps come from the committed Phase 1 table. When the incumbent is the runner-up, the test is the row's `margin_pct`.
  - When the incumbent has fallen to #3 or lower, the buffer counts as exceeded. That happens once, 2025-06-30, when Nvidia led Apple by 26% (quarter-end caps in the local market-cap file).
  - Four LOW-confidence rows name a #1 whose estimated cap is slightly below the runner-up's (−0.1% to −1.0%): the #1 was set by source anchors, within the estimate's error. There an incumbent runner-up is kept at any buffer.
  - Like every picker here, it only redirects new contributions; existing lots are never sold.
- **The #2** (`rank`, `n = 2`). "The highest market cap among ranks 2–5" is by definition the #2, i.e. the table's runner-up. It is available for all 205 quarters.
- **Ranks 2–5 equal-weight** (`ranks_ew`, `first = 2`, `last = 5`). $125 each in ranks 2–5. This is the other reasonable reading of "#2–5". Run only from **2006-04-01**, where top-10 lists are complete.
- **Switches** (`pick_switches.csv`): quarters in which the set of names receiving new money changes. The #1 is re-run in this family as the reference for switch counts; its values are identical to top1_core.

Sharpe/Sortino and max drawdown: monthly returns of the stock leg's time-weighted unit value vs 3-month T-bills ([definitions](risk_metrics.md)).

## 1975–2026

| Picker         | Rule              | Window    | Switches | Distinct names | Stock-leg final |   XIRR | Sharpe | Sortino | Max DD | Index XIRR | Index Sharpe |
| -------------- | ----------------- | --------- | -------: | -------------: | --------------: | -----: | -----: | ------: | -----: | ---------: | -----------: |
| #1 (reference) | Baseline hold     | 1975–2026 |       39 |              8 |      $2,460,375 |  9.73% |   0.43 |    0.68 |   −57% |     11.87% |         0.58 |
| #1, 5% buffer  | Baseline hold     | 1975–2026 |       28 |              7 |      $2,453,009 |  9.72% |   0.42 |    0.67 |   −56% |     11.87% |         0.58 |
| #1, 5% buffer  | Trailing stop 25% | 1975–2026 |       28 |              7 |      $5,188,096 | 11.71% |   0.57 |    0.87 |   −53% |     11.87% |         0.58 |
| #1, 5% buffer  | Buy the dip       | 1975–2026 |       28 |              7 |      $5,685,172 | 10.31% |   0.41 |    0.65 |   −58% |     11.87% |         0.58 |
| #1, 10% buffer | Baseline hold     | 1975–2026 |       20 |              7 |      $2,503,659 |  9.77% |   0.43 |    0.68 |   −57% |     11.87% |         0.58 |
| #1, 20% buffer | Baseline hold     | 1975–2026 |       14 |              7 |      $2,445,261 |  9.71% |   0.43 |    0.68 |   −57% |     11.87% |         0.58 |
| #2             | Baseline hold     | 1975–2026 |       69 |             15 |      $3,241,425 | 10.47% |   0.52 |    0.83 |   −51% |     11.87% |         0.58 |
| #2             | Trailing stop 25% | 1975–2026 |       69 |             15 |      $6,944,453 | 12.48% |   0.66 |    1.03 |   −48% |     11.87% |         0.58 |
| #2             | Buy the dip       | 1975–2026 |       69 |             15 |      $5,298,455 | 10.64% |   0.53 |    0.86 |   −52% |     11.87% |         0.58 |

## 1995–2026 (fresh runs)

| Picker         | Rule              | Window    | Switches | Distinct names | Stock-leg final |   XIRR | Sharpe | Sortino | Max DD | Index XIRR | Index Sharpe |
| -------------- | ----------------- | --------- | -------: | -------------: | --------------: | -----: | -----: | ------: | -----: | ---------: | -----------: |
| #1 (reference) | Baseline hold     | 1995–2026 |       21 |              5 |        $442,341 | 10.66% |   0.52 |    0.82 |   −76% |     10.68% |         0.62 |
| #1, 5% buffer  | Baseline hold     | 1995–2026 |       17 |              5 |        $444,973 | 10.68% |   0.52 |    0.82 |   −77% |     10.68% |         0.62 |
| #1, 5% buffer  | Trailing stop 25% | 1995–2026 |       17 |              5 |        $486,328 | 11.12% |   0.66 |    1.08 |   −53% |     10.68% |         0.62 |
| #1, 5% buffer  | Buy the dip       | 1995–2026 |       17 |              5 |      $1,088,213 | 11.35% |   0.54 |    0.85 |   −77% |     10.68% |         0.62 |
| #1, 10% buffer | Baseline hold     | 1995–2026 |       11 |              5 |        $445,813 | 10.69% |   0.53 |    0.83 |   −76% |     10.68% |         0.62 |
| #1, 20% buffer | Baseline hold     | 1995–2026 |        7 |              5 |        $381,227 |  9.93% |   0.47 |    0.72 |   −82% |     10.68% |         0.62 |
| #2             | Baseline hold     | 1995–2026 |       43 |             12 |        $545,090 | 11.67% |   0.57 |    0.87 |   −53% |     10.68% |         0.62 |
| #2             | Trailing stop 25% | 1995–2026 |       43 |             12 |        $466,901 | 10.92% |   0.60 |    0.90 |   −50% |     10.68% |         0.62 |
| #2             | Buy the dip       | 1995–2026 |       43 |             12 |      $1,138,509 | 11.88% |   0.53 |    0.81 |   −60% |     10.68% |         0.62 |

## 2006–2026 (complete top-10 lists)

| Picker                 | Rule              | Window    | Switches | Distinct names | Stock-leg final |   XIRR | Sharpe | Sortino | Max DD | Index XIRR | Index Sharpe |
| ---------------------- | ----------------- | --------- | -------: | -------------: | --------------: | -----: | -----: | ------: | -----: | ---------: | -----------: |
| #1 (reference)         | Baseline hold     | 2006–2026 |       12 |              4 |        $230,590 | 15.53% |   0.67 |    1.13 |   −37% |     13.41% |         0.66 |
| #2                     | Baseline hold     | 2006–2026 |       21 |              8 |        $271,764 | 16.86% |   0.51 |    0.74 |   −80% |     13.41% |         0.66 |
| Ranks 2–5 equal-weight | Baseline hold     | 2006–2026 |       40 |             19 |        $272,672 | 16.89% |   0.64 |    0.95 |   −68% |     13.41% |         0.66 |
| Ranks 2–5 equal-weight | Trailing stop 25% | 2006–2026 |       40 |             19 |        $207,938 | 14.68% |   0.64 |    0.94 |   −61% |     13.41% |         0.66 |
| Ranks 2–5 equal-weight | Buy the dip       | 2006–2026 |       40 |             19 |        $471,366 | 16.95% |   0.57 |    0.81 |   −75% |     13.41% |         0.66 |

## What this says

**The margin buffer cuts churn without changing the result.**

- **Switch counts.** A 5% buffer cuts switches from 39 to 28 (1975–2026) and from 21 to 17 (1995–2026). 10% and 20% buffers get down to 20 and 14.
- **Returns.** Every buffered baseline run lands within 0.06 pp of the plain #1 over 1975–2026. The 15 quarters where the 5% buffer bought something else split both ways: it held IBM through old AT&T's 1977 lead, Exxon through AT&T Corp's and GE's thin 1993–94 leads (so it never bought AT&T Corp at all), and GE and Microsoft through each other's brief overtakes.
- **Too sticky costs money.** At 20% the buffer kept buying GE through 2005–07 while Exxon led. That cost 0.73 pp over 1995–2026 (9.93% vs 10.66%) and deepened the drawdown to −82%.
- **Verdict.** Churn in the #1 is mostly noise between near-equal giants. A small buffer is harmless and saves trades; a large one is a bet on the incumbent.

**The #2 did better than the #1, and with less risk.**

- **1975–2026:** 10.47% vs 9.73% XIRR (+$0.78M), Sharpe 0.52 vs 0.43, worst drawdown −51% vs −57%.
- **1995–2026:** 11.67% vs 10.66%, and it beats the index on XIRR (the #1 only ties).
- **Why.** The #2 changes much more often (69 switches, 15 names vs 8), which spreads money over more companies. In several of the #1's worst stretches it bought something else: Exxon instead of IBM in 1985–89, GE instead of Microsoft in 2000, Exxon instead of GE in 2001.
- **Not a free lunch.** Over 2006–2026 the #2 beat the #1 on XIRR (16.86% vs 15.53%) but with a −80% drawdown: it bought GE in every quarter from 2006-04 to 2008-10. Its Sharpe was 0.51 vs 0.67.
- **The trailing stop helps the #2 over 1975–2026** (12.48%, the only baseline-picker variant above the index that far back) **but hurts it over 1995–2026** (10.92%).

**Ranks 2–5 equal-weight (2006–2026) is between the two.** 16.89% XIRR vs 15.53% for the #1, but a Sharpe of 0.64 vs 0.67 and a −68% drawdown. Spreading across four names didn't make up for owning 2008's hardest-hit giants (trough 2009-03-09).

**Overall.** Nothing in this family suggests the #1 slot is special. Its runner-up did as well or better in every window. The #1's weakness is the regime risk of whichever single giant is on top, which the [rolling windows](rolling_windows.md) and the [placebo](random_pick_placebo.md) also show.

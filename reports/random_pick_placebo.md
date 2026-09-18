# Random-pick placebo: is the #1 special?

[← index](../REPORT.md) · config: [`scenarios/random_pick_placebo.toml`](../scenarios/random_pick_placebo.toml) · results: [`results/random_pick_placebo/`](../results/random_pick_placebo/)

**Question.** Does buying the single largest company add anything beyond "own some mega-cap"? Or would any top-10 stock, held the same way, have done about as well?

**Design.**

- 1,000 independent simulations. Each quarter from **2006-04-01**, one ticker is drawn uniformly at random from that quarter's top-10 list and held with the baseline-hold rule ($500/quarter, valued 2026-01-02).
- 2006-04-01 is the first quarter with a COMPLETE top-10 list; the 2006-01-01 list is PARTIAL. It is also the start of the existing #1 comparison run, so the ranking is like-for-like.
- The #1 itself is one of the ten candidates, so random runs drew it in 10.2% of quarters on average.
- Seeds are `20260918 + i`, so every run is reproducible.
- Only per-run summary statistics are stored (`sims.csv`: XIRR, plus Sharpe, Sortino and max drawdown per leg); lot-by-lot histories are not.
- The window is not extended before 2006: a reliable random-draw universe there would need the same point-in-time research as the original #1 table.

| Random-pick stock-leg XIRR             |                             Value |
| -------------------------------------- | --------------------------------: |
| Mean / median                          |                   14.94% / 14.96% |
| Standard deviation                     |                           0.93 pp |
| 5th / 25th / 75th / 95th percentile    | 13.47% / 14.29% / 15.56% / 16.47% |
| Min / max                              |                   11.93% / 17.59% |
| Index leg, same window                 |                            13.41% |
| Share of random runs beating the index |                             96.0% |

| Reference strategy                 |   XIRR | Percentile rank among 1,000 random runs | z-score |
| ---------------------------------- | -----: | --------------------------------------: | ------: |
| **#1 picker, baseline hold**       | 15.53% |                                **74th** |    0.63 |
| Top-10 equal-weight, baseline hold | 15.00% |                                    52nd |    0.07 |

**Risk-adjusted** (monthly Sharpe and Sortino against 3-month T-bills, max drawdown of the daily unit value; [definitions](risk_metrics.md)):

| Random-pick stock leg                                    |             Sharpe |            Sortino |       Max drawdown |
| -------------------------------------------------------- | -----------------: | -----------------: | -----------------: |
| Mean                                                     |               0.70 |               1.07 |               −53% |
| 5th / 50th / 95th percentile                             | 0.55 / 0.70 / 0.84 | 0.80 / 1.07 / 1.35 | −68% / −53% / −38% |
| Index leg, same window                                   |               0.66 |               0.98 |               −55% |
| Share of random runs with a higher Sharpe than the index |              67.6% |                    |                    |

| Reference strategy                 | Sharpe | Sharpe percentile rank | Max drawdown | Share of random runs with a deeper drawdown |
| ---------------------------------- | -----: | ---------------------: | -----------: | ------------------------------------------: |
| **#1 picker, baseline hold**       |   0.67 |               **38th** |         −37% |                                       96.1% |
| Top-10 equal-weight, baseline hold |   0.73 |                   63rd |         −51% |                                       55.6% |

> **Corrected 2026-09-18.** The first version of this page drew from top-10 lists that were missing Google in 19 quarters (2008–2014; see [methodology](methodology.md)). With Google restored:
>
> - the random-pick mean rose from 14.58% to 14.94%;
> - the #1 picker's rank fell from the 80th to the 74th percentile (38th on Sharpe, was 42nd);
> - the conclusions below were only strengthened.

![Placebo XIRR distribution](../charts/random_pick_placebo/xirr_distribution.png)
_Random single-stock picks from each quarter's top-10 (grey), with the real #1 picker (blue), top-10 equal-weight (purple) and the index leg (black dashed)._

**Interpretation.**

- **The #1 picker is not in a tail.** It sits at the 74th percentile, about two-thirds of a standard deviation above the random mean: one in four random mega-cap sequences did as well or better. That is weak evidence at best that picking the #1 beat a random mega-cap, nowhere near the 5% tail that would mark a distinctive edge. Over 2006–2026 the "#1" framing adds at most a modest, statistically unremarkable edge over "own a random mega-cap".
- **Most of the outperformance comes from the era, not the pick.** 96% of the random runs beat the index, and the average random pick earned 14.94% against the index's 13.41%. Of the #1 picker's +2.1 pp over the index in this window, about +1.5 pp is plain mega-cap exposure (the average random pick) and only about +0.6 pp is specific to picking the #1.
- **Risk-adjusted, the #1's edge disappears.** It ranks 74th on XIRR but only 38th on Sharpe, below the median random pick.
  - Its extra return came with extra volatility: from 2012 every new dollar went into one stock at a time (Apple, then Microsoft and Nvidia), so a few names dominated the leg.
  - Its drawdown is unusually shallow (−37%, shallower than 96% of random runs) only because Exxon, the #1 from 2006 to 2011, fell less than most mega-caps in 2008–09.
  - Top-10 equal-weight, which is simply more diversified, ranks higher on Sharpe (63rd) than the #1.
- **Equal-weighting the top-10 is exactly the "typical" outcome.** It lands at the 52nd percentile, as expected for an average of the draws.
- **Caveat:** this is one 20-year window that happened to reward mega-caps. It says nothing about 1975–1995, when the #1 (IBM, then old AT&T) did much worse than the index, and it cannot be extended there without new data work.

# Top-10 equal-weight vs #1, 2006–2026

[← index](../REPORT.md) · config: [`scenarios/top10_ew.toml`](../scenarios/top10_ew.toml) · results: [`results/top10_ew/`](../results/top10_ew/)

## Top-10 equal-weight variant (2006-04-01 → 2026-01-02)

Top-10 lists are only COMPLETE from the 2006-03-31 observation. Before that they are either missing or survivorship-biased (see [methodology: known gaps](methodology.md#known-gaps-and-data-caveats-logged-not-hidden)), so this variant covers 80 quarters. The #1 pick is shown over the same window for comparison.

| Scenario                         | Strategy invested | Strategy ending value | Multiple |   XIRR | Sharpe | Sortino | Max DD | Index invested | Index ending value | Multiple |   XIRR | Sharpe | Sortino | Max DD | Combined value | Combined multiple | Combined XIRR | Combined Sharpe |
| -------------------------------- | ----------------: | --------------------: | -------: | -----: | -----: | ------: | -----: | -------------: | -----------------: | -------: | -----: | -----: | ------: | -----: | -------------: | ----------------: | ------------: | --------------: |
| Top-10 EW — baseline             |           $40,000 |              $216,350 |    5.41x | 15.00% |   0.73 |    1.12 |   −51% |        $40,000 |           $178,311 |    4.46x | 13.41% |   0.66 |    0.98 |   −55% |       $394,661 |             4.93x |        14.25% |            0.71 |
| Top-10 EW — trailing stop        |           $40,000 |              $170,451 |    4.26x | 13.04% |   0.68 |    1.03 |   −48% |        $40,000 |           $178,311 |    4.46x | 13.41% |   0.66 |    0.98 |   −55% |       $348,762 |             4.36x |        13.23% |            0.67 |
| Top-10 EW — buy the dip          |           $76,450 |              $402,173 |    5.26x | 16.00% |   0.66 |    0.97 |   −62% |        $40,000 |           $178,311 |    4.46x | 13.41% |   0.66 |    0.98 |   −55% |       $580,484 |             4.98x |        15.08% |            0.67 |
| #1 (same window) — baseline      |           $40,000 |              $230,590 |    5.76x | 15.53% |   0.67 |    1.13 |   −37% |        $40,000 |           $178,311 |    4.46x | 13.41% |   0.66 |    0.98 |   −55% |       $408,901 |             5.11x |        14.54% |            0.72 |
| #1 (same window) — trailing stop |           $40,000 |              $153,060 |    3.83x | 12.14% |   0.67 |    1.05 |   −35% |        $40,000 |           $178,311 |    4.46x | 13.41% |   0.66 |    0.98 |   −55% |       $331,371 |             4.14x |        12.80% |            0.70 |
| #1 (same window) — buy the dip   |           $84,500 |              $470,083 |    5.56x | 17.30% |   0.70 |    1.17 |   −37% |        $40,000 |           $178,311 |    4.46x | 13.41% |   0.66 |    0.98 |   −55% |       $648,394 |             5.21x |        15.96% |            0.73 |

Sharpe, Sortino and max drawdown: monthly time-weighted returns vs 3-month T-bills ([definitions](risk_metrics.md)).

- **Top-10 EW vs the #1.** The #1 earns more (15.53% vs 15.00% XIRR) with a slightly lower Sharpe (0.67 vs 0.73).
- **Drawdowns.** In 2008–09 the #1 (Exxon, every quarter from 2006-04 to 2011-07) fell less than the top-10 basket: −37% vs −51%.
- **Buy-the-dip.** Its XIRR lead does not survive risk adjustment on the top-10 basket: Sharpe 0.66 vs 0.72 for plain holding, and a −62% worst drawdown.

2006–2026 was the mega-cap-tech era (Apple, Microsoft, Nvidia), so both concentrated strategies beat the index here. The trailing stop hurt in this window: stops fired in clusters (2008–09, 2015–16, 2018–20, 2022), and each time the proceeds sat in the index while the mega-caps rebounded.

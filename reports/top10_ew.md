# Top-10 equal-weight vs #1, 2006–2026

[← index](../REPORT.md) · config: [`scenarios/top10_ew.toml`](../scenarios/top10_ew.toml) · results: [`results/top10_ew/`](../results/top10_ew/)

## Top-10 equal-weight variant (2006-04-01 → 2026-01-02)

Top-10 lists are only COMPLETE from the 2006-03-31 observation. Before that they are either missing or survivorship-biased (see [methodology: known gaps](methodology.md#known-gaps-and-data-caveats-logged-not-hidden)), so this variant covers 80 quarters. The #1 pick is shown over the same window for comparison.

| Scenario                         | Strategy invested | Strategy ending value | Multiple |   XIRR | Index invested | Index ending value | Multiple |   XIRR | Combined value | Combined multiple | Combined XIRR |
| -------------------------------- | ----------------: | --------------------: | -------: | -----: | -------------: | -----------------: | -------: | -----: | -------------: | ----------------: | ------------: |
| Top-10 EW — baseline             |           $40,000 |              $207,746 |    5.19x | 14.67% |        $40,000 |           $178,311 |    4.46x | 13.41% |       $386,057 |             4.83x |        14.07% |
| Top-10 EW — trailing stop        |           $40,000 |              $165,584 |    4.14x | 12.80% |        $40,000 |           $178,311 |    4.46x | 13.41% |       $343,894 |             4.30x |        13.11% |
| Top-10 EW — buy the dip          |           $76,200 |              $402,165 |    5.28x | 16.00% |        $40,000 |           $178,311 |    4.46x | 13.41% |       $580,475 |             5.00x |        15.09% |
| #1 (same window) — baseline      |           $40,000 |              $230,590 |    5.76x | 15.53% |        $40,000 |           $178,311 |    4.46x | 13.41% |       $408,901 |             5.11x |        14.54% |
| #1 (same window) — trailing stop |           $40,000 |              $153,060 |    3.83x | 12.14% |        $40,000 |           $178,311 |    4.46x | 13.41% |       $331,371 |             4.14x |        12.80% |
| #1 (same window) — buy the dip   |           $84,500 |              $470,083 |    5.56x | 17.30% |        $40,000 |           $178,311 |    4.46x | 13.41% |       $648,394 |             5.21x |        15.96% |

2006–2026 was the mega-cap-tech era (Apple, Microsoft, Nvidia), so both concentrated strategies beat the index here. The trailing stop hurt in this window: stops fired in clusters (2008–09, 2015–16, 2018–20, 2022), and each time the proceeds sat in the index while the mega-caps rebounded.

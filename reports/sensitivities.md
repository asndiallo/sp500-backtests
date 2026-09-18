# Sensitivities: confidence grades, pre-1996 data, AT&T breakup

[← index](../REPORT.md) · configs: [`scenarios/data_sensitivity.toml`](../scenarios/data_sensitivity.toml), [`scenarios/corp_action_sensitivity.toml`](../scenarios/corp_action_sensitivity.toml) · results: [`results/data_sensitivity/`](../results/data_sensitivity/), [`results/corp_action_sensitivity/`](../results/corp_action_sensitivity/)

## How much of the conclusion rests on shaky data?

The confidence grades and their share of ending value are in [top1_core](top1_core.md#how-much-of-the-conclusion-rests-on-shaky-data).

Sensitivity of each rule's strategy-leg XIRR (and ending value):

| Sensitivity                                      |   Baseline hold | Trailing stop 25% |     Buy the dip |
| ------------------------------------------------ | --------------: | ----------------: | --------------: |
| Main result (as built)                           |  9.73% ($2.46M) |   11.72% ($5.20M) | 10.28% ($5.57M) |
| LOW rows switched to their alt pick              |  9.69% ($2.43M) |   11.63% ($5.02M) | 10.33% ($5.83M) |
| LOW rows → index instead of #1                   | 10.06% ($2.78M) |   11.66% ($5.09M) | 10.46% ($5.79M) |
| MEDIUM+LOW rows → index                          | 11.56% ($4.90M) |   11.79% ($5.33M) | 11.54% ($5.97M) |
| All pre-1996 rows → index                        | 11.88% ($5.52M) |   11.87% ($5.51M) | 11.90% ($6.15M) |
| Window 1996-01-01 onward only (index leg 10.66%) |          10.85% |            10.63% |          11.63% |

Reading it:

- **The 11 LOW rows barely matter to _which_ stock was picked.** Replacing each with its runner-up moves results by ≤0.2 pp, because the contested pairs (IBM vs AT&T in 1977–82, Exxon vs IBM in 1990, GE vs AT&T Corp in 1994–95) mostly had similar subsequent paths.
- **The underperformance is an era result, and that era is where the data is weakest.** The 84 pre-1996 contributions ($42,000) ended at about $3.1M _less_ than the same money in the index. The main culprits are IBM lots bought in 1983–1990 (IBM fell ~75% from its 1987 peak to 1993) and the AT&T basket (below). In the better-sourced 1996–2026 period, the #1 strategy was roughly index-like.
- **Whether a MEDIUM row picked the right #1 barely matters; how the pre-1996 picks performed matters a lot.** If you distrust the 1975–1995 estimates entirely, the defensible conclusion is the 1996+ one: owning the #1 was about as good as owning the index.

## Corporate-action and continuity decisions that moved the result

1. **AT&T's 1984 breakup (material).** Old AT&T was #1 at 16 quarter starts (1975-01, 1977-07/10, 1978-04/07/10, 1980-04/07/10, 1981-04 through 1982-10). Each lot is held through divestiture and split by the IRS basis allocation:
   - 28.67% into new AT&T Corp, tracked on its own monthly series to the 2005 SBC merger.
   - 46.37% into the SBC line (Yahoo `T`): Southwestern Bell exactly, plus Ameritech, Pacific Telesis and BellSouth, which were absorbed into SBC/AT&T Inc later and are proxied by SBC before their mergers.
   - 24.96% into the Bell Atlantic line (`VZ`): Bell Atlantic exactly, plus NYNEX (merged in 1997).
   - US West (9.0%) is proxied half-and-half by SBC and Bell Atlantic.

   Each 1984 dollar of this basket grew 62× by 2026, vs 108× for the index. Treatment changes the result materially:
   - **Selling old AT&T at the 1983-12-30 close** and moving the proceeds to the index instead lifts the baseline to 10.29% (+0.56 pp, **+$579k**, +24% of strategy value). It _lowers_ the trailing-stop result to 11.41% (−0.31 pp). The basket beat the index from 1984 to 2000 (19.5× vs 14.3×) before the telecom bust, and under the trailing stop most basket lots were stopped into the index in 2000–02, near that peak. Selling in 1983 gives up that run.
   - **Writing US West's share off entirely** (a lower bound for its real Qwest/CenturyLink path) costs only −0.09 pp / −$80k.
   - The old-AT&T lineage is **$0.78M of the baseline's $2.46M**.

2. **SBC acquisition of AT&T Corp (2005-11-18).** The consideration was 0.77942 SBC shares **plus a $1.30/share special dividend**, per the merger proxy on EDGAR. Modelling only the share ratio would have silently lost 6.4% of every AT&T Corp lot. The cash is sent to the index leg, per the framework's convention for deal cash.
3. **Old-GM bankruptcy (2009) does not arise.** GM never ranked #1 at a quarter-end in 1975–2026 (Morgan Stanley's data last shows it in the top 3 in 1971). The `bankruptcy` mode exists in the engine but is unused.
4. **Exxon + Mobil (1999).** Exxon was the acquirer and legal survivor; the ticker moved from XON to XOM, and Yahoo's XOM history is Exxon's, so it is continuous with no action needed. All 25 of XOM's post-1999 #1 quarters are flagged "merged entity" in `structural_flag`. Its 2005–2013 dominance reflects a company roughly doubled by merger, plus the oil price.
5. **Spinoffs inside Yahoo's adjusted prices** (IBM/Kyndryl, the three GE spins, AT&T/WBD, Verizon's three spins, Pfizer/Viatris, Altria's Kraft and PMI spins booked as special dividends) are treated as "value reinvested in the parent". I checked the implied value fraction against the documented distribution terms, all within 1.8 pp (`results/data_quality/price_sanity.csv`). No spinoff value is lost; it is simply not held as the separate stock.
6. **Ticker reuse.** Yahoo's `T` before Nov 2005 is **SBC**, not AT&T. Old AT&T (to 1983) and AT&T Corp (1984–2005) therefore use hand-built series (`T_OLD`, `T_CORP`), never Yahoo's `T`. Every other symbol used is a continuous legal entity on Yahoo: IBM, XOM, GE (now GE Aerospace), MSFT, AAPL, NVDA, and the top-10 names (`data/universe.csv`, `continuity_note`).

Structural caveats on #1 spells that reflect a corporate event rather than organic strength are in the table's `structural_flag` column:

- **Pre-breakup AT&T (1982–83):** the divestiture had already been agreed (1982-01-08).
- **AT&T Corp at 1994-10-01:** inflated by the McCaw Cellular stock deal.
- **Post-merger Exxon.**

Every #1 change, with the relative price move and dated news context, is in `data/top1_transitions.csv`.

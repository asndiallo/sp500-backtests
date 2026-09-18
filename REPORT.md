# Buying the #1 S&P 500 company every quarter, 1975–2026

**Setup.** On every quarter start from 1975-01-01 to 2026-01-01 (205 dates), $500 buys the largest S&P 500 company _as of the previous quarter-end close_ (no lookahead). Another $500 buys the S&P 500 total-return index. Everything is valued at the 2026-01-02 close. XIRRs are solved with `scipy.optimize.brentq` on the actual dated cashflows (`sp500bt/metrics.py`). They replace the old "multiple^(1/years)" approximation, which also ignored the index leg's contributions and the buy-the-dip top-ups.

**Bottom line.**

- **Buying and holding the #1 company underperformed the index:** 9.73% vs 11.87% XIRR, or $2.46M vs $5.51M from the same $102,500.
- **The gap comes entirely from 1975–1995 picks.** Routing only the pre-1996 picks to the index makes the strategy match the index (11.88%). A fresh backtest started on 1995-01-01 confirms it: the #1 stock leg ties the index (10.66% vs 10.68%), and both active rules beat it (see the cross-window comparison below).
- **Risk-adjusted, the #1 is worse than its XIRR suggests.** Over 1995–2026 the baseline ties the index on XIRR, but with 21% vs 15% volatility and a Sharpe of 0.52 vs 0.62. Its drawdown was −76%, and it took 18 years (2000–2018) to regain its peak. Only the trailing stop keeps up with the index on Sharpe: it is a hair below over 1975–2026 (0.575 vs 0.582) and above over 1995–2026 (0.67 vs 0.62) ([risk metrics](reports/risk_metrics.md)).
- **The 1995–2026 tie is one window, not a property of the strategy.** Across all 435 rolling 10/15/20-year windows since 1975, the #1 beat the index in only 30–36% of them. It had the better Sharpe in 22%, 10% and 0.8% (1 of 125) of 10-, 15- and 20-year windows ([rolling windows](reports/rolling_windows.md)).
- **Nothing about the #1 slot is special.**
  - Among 1,000 random top-10 pickers over 2006–2026, the #1 ranks at the 74th percentile on XIRR and the 38th on Sharpe ([placebo](reports/random_pick_placebo.md)).
  - The runner-up beat the #1 in every window tested ([alt pickers](reports/alt_pickers.md)).
  - An equal-weight top-3 beat it on both return and Sharpe over 2009–2026 ([breadth](reports/breadth.md)).
  - A growth-plus-margin screen of the top 10 only matched it ([fundamentals](reports/fundamentals_picker.md)).
- **The plain 25% trailing stop is the only rule that holds up, and none of its refinements beats it.**
  - Partial trims, stop-and-rebuy and volatility-scaled stops all do worse over 1975–2026 ([rule variants](reports/rule_variants.md)).
  - Capital-gains tax costs it only about 0.2–0.4 pp and changes no ranking ([tax drag](reports/tax_drag.md)).
  - Contribution cadence (monthly, quarterly, annual lump sum) moves nothing by more than 0.15 pp ([cadence](reports/cadence.md)).
- **The conclusion rests on the least certain part of the data, but not on the ambiguous rows within it.** Swapping every LOW-confidence pick for its runner-up moves the result by only −0.04 pp. What drives it is IBM's 1987–93 collapse and the AT&T breakup, not uncertainty about who was #1.

## Headline comparison

| Scenario                           | Window                          | Stock-leg invested | Stock-leg final | Stock-leg XIRR | Stock Sharpe | Stock Sortino | Stock max DD | Index-leg invested | Index-leg final | Index-leg XIRR | Index Sharpe | Index Sortino | Index max DD | Combined final | Combined XIRR | Combined Sharpe |
| ---------------------------------- | ------------------------------- | -----------------: | --------------: | -------------: | -----------: | ------------: | -----------: | -----------------: | --------------: | -------------: | -----------: | ------------: | -----------: | -------------: | ------------: | --------------: |
| Baseline hold                      | 1975–2026                       |           $102,500 |      $2,460,375 |          9.73% |         0.43 |          0.68 |         −57% |           $102,500 |      $5,508,523 |         11.87% |         0.58 |          0.87 |         −55% |     $7,968,898 |        11.02% |            0.55 |
| 25% trailing stop → index          | 1975–2026                       |           $102,500 |      $5,200,079 |         11.72% |         0.58 |          0.88 |         −53% |           $102,500 |      $5,508,523 |         11.87% |         0.58 |          0.87 |         −55% |    $10,708,602 |        11.80% |            0.59 |
| Buy the dip −25%/−50%              | 1975–2026                       |           $270,500 |      $5,565,832 |         10.28% |         0.42 |          0.67 |         −58% |           $102,500 |      $5,508,523 |         11.87% |         0.58 |          0.87 |         −55% |    $11,074,355 |        11.00% |            0.52 |
| Baseline hold                      | 1995–2026                       |            $62,500 |        $442,341 |         10.66% |         0.52 |          0.82 |         −76% |            $62,500 |        $444,487 |         10.68% |         0.62 |          0.92 |         −55% |       $886,828 |        10.67% |            0.59 |
| 25% trailing stop → index          | 1995–2026                       |            $62,500 |        $488,826 |         11.14% |         0.67 |          1.08 |         −53% |            $62,500 |        $444,487 |         10.68% |         0.62 |          0.92 |         −55% |       $933,313 |        10.92% |            0.66 |
| Buy the dip −25%/−50%              | 1995–2026                       |           $150,500 |      $1,078,642 |         11.30% |         0.54 |          0.84 |         −77% |            $62,500 |        $444,487 |         10.68% |         0.62 |          0.92 |         −55% |     $1,523,129 |        11.10% |            0.57 |
| Top-10 equal-weight, baseline hold | **2006–2026 (from 2006-04-01)** |            $40,000 |        $216,350 |         15.00% |         0.73 |          1.12 |         −51% |            $40,000 |        $178,311 |         13.41% |         0.66 |          0.98 |         −55% |       $394,661 |        14.25% |            0.71 |

Source: [`results/scenario_comparison.csv`](results/scenario_comparison.csv); the risk columns come from [`results/risk_metrics.csv`](results/risk_metrics.csv).

- Sharpe and Sortino use monthly returns of each leg's time-weighted unit value against 3-month T-bills (FRED TB3MS).
- Max DD is the worst peak-to-trough fall of the daily unit value.
- Definitions and the full table (volatility, downside deviation, recovery dates) are in [reports/risk_metrics.md](reports/risk_metrics.md).

The buy-the-dip "invested" figures include its top-ups. **The top-10 row runs on a different window** (2006-04-01 → 2026-01-02, the only period with complete top-10 lists), so compare it only with its own index leg, not with the 1995–2026 rows.

![XIRR by rule and window](charts/summary/xirr_by_window.png)

## Extended comparison: pickers, rules, breadth, cadence

Key variants from the later scenario families, built by the same summary step from `scenarios/_summary.toml` ([`results/extended_comparison.csv`](results/extended_comparison.csv)). **Rows sit on different windows**: compare each row only with its own index leg and with the reference row of its section.

| Section                     | Variant                                 | Window    | Stock-leg XIRR | Index XIRR | Stock − index | Stock Sharpe | Index Sharpe | Stock max DD | Report                                                |
| --------------------------- | --------------------------------------- | --------- | -------------: | ---------: | ------------: | -----------: | -----------: | -----------: | ----------------------------------------------------- |
| Pickers                     | #1 (reference)                          | 1975–2026 |          9.73% |     11.87% |      −2.15 pp |         0.43 |         0.58 |         −57% | [top1_core](reports/top1_core.md)                     |
| Pickers                     | #1 with a 5% margin buffer              | 1975–2026 |          9.72% |     11.87% |      −2.15 pp |         0.42 |         0.58 |         −56% | [alt_pickers](reports/alt_pickers.md)                 |
| Pickers                     | #2 (runner-up)                          | 1975–2026 |         10.47% |     11.87% |      −1.41 pp |         0.52 |         0.58 |         −51% | [alt_pickers](reports/alt_pickers.md)                 |
| Pickers                     | #2 (runner-up)                          | 1995–2026 |         11.67% |     10.68% |      +0.99 pp |         0.57 |         0.62 |         −53% | [alt_pickers](reports/alt_pickers.md)                 |
| Pickers                     | #1 (reference)                          | 2012–2026 |         24.57% |     14.74% |      +9.83 pp |         0.80 |         0.92 |         −44% | [fundamentals_picker](reports/fundamentals_picker.md) |
| Pickers                     | Best growth + margin rank in the top 10 | 2012–2026 |         23.75% |     14.74% |      +9.01 pp |         0.88 |         0.92 |         −44% | [fundamentals_picker](reports/fundamentals_picker.md) |
| Rules (#1)                  | 25% trailing stop (reference)           | 1975–2026 |         11.72% |     11.87% |      −0.15 pp |         0.58 |         0.58 |         −53% | [top1_core](reports/top1_core.md)                     |
| Rules (#1)                  | Partial trim: 50% at −25%, once per lot | 1975–2026 |         10.91% |     11.87% |      −0.96 pp |         0.53 |         0.58 |         −51% | [rule_variants](reports/rule_variants.md)             |
| Rules (#1)                  | 25% stop + rebuy on regaining #1        | 1975–2026 |         10.42% |     11.87% |      −1.45 pp |         0.49 |         0.58 |         −53% | [rule_variants](reports/rule_variants.md)             |
| Rules (#1)                  | Volatility-scaled stop (k = 1)          | 1975–2026 |         11.56% |     11.87% |      −0.32 pp |         0.56 |         0.58 |         −55% | [rule_variants](reports/rule_variants.md)             |
| Breadth (common window)     | #1                                      | 2009–2026 |         19.33% |     14.71% |      +4.61 pp |         0.79 |         1.01 |         −34% | [breadth](reports/breadth.md)                         |
| Breadth (common window)     | Top-3 equal-weight                      | 2009–2026 |         21.17% |     14.71% |      +6.46 pp |         1.06 |         1.01 |         −29% | [breadth](reports/breadth.md)                         |
| Breadth (common window)     | Top-10 equal-weight                     | 2009–2026 |         17.59% |     14.71% |      +2.88 pp |         1.10 |         1.01 |         −29% | [breadth](reports/breadth.md)                         |
| Breadth (common window)     | Top-20 equal-weight                     | 2009–2026 |         15.56% |     14.71% |      +0.85 pp |         1.03 |         1.01 |         −30% | [breadth](reports/breadth.md)                         |
| Cadence (#1, baseline hold) | Monthly $166.67                         | 1975–2026 |          9.74% |     11.86% |      −2.12 pp |         0.43 |         0.58 |         −57% | [cadence](reports/cadence.md)                         |
| Cadence (#1, baseline hold) | Annual lump sum $2,000                  | 1975–2026 |          9.66% |     11.93% |      −2.27 pp |         0.41 |         0.58 |         −56% | [cadence](reports/cadence.md)                         |

## Scenario families

Every scenario ever run is listed in [`scenarios/index.csv`](scenarios/index.csv) (id, window, date added, status, results, report). Each family has one config in `scenarios/`, its outputs in `results/<id>/` and `charts/<id>/`, and a report page:

| Family                                        | What it tests                                                                                                                                               | Report                                                           |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `top1_core`                                   | #1 company × baseline hold / 25% trailing stop / buy-the-dip, 1975–2026 and fresh 1995–2026 runs; reconciliation; confidence attribution                    | [reports/top1_core.md](reports/top1_core.md)                     |
| `top10_ew`                                    | Top-10 equal-weight vs #1 over 2006–2026                                                                                                                    | [reports/top10_ew.md](reports/top10_ew.md)                       |
| `data_sensitivity`, `corp_action_sensitivity` | Confidence grades, pre-1996 data, AT&T 1984 breakup treatment                                                                                               | [reports/sensitivities.md](reports/sensitivities.md)             |
| `random_pick_placebo`                         | 1,000 random top-10 picks per quarter vs the #1 (2006–2026): the #1 ranks at the 74th percentile (38th on Sharpe)                                           | [reports/random_pick_placebo.md](reports/random_pick_placebo.md) |
| `tax_drag`                                    | Capital-gains tax on realizations (illustrative 15%/32% and 23.8%/40.8%), before and after liquidation: ranking unchanged                                   | [reports/tax_drag.md](reports/tax_drag.md)                       |
| `rolling_windows`                             | #1 minus index XIRR for all 435 10/15/20-year windows: regime-driven, not converging to a tie                                                               | [reports/rolling_windows.md](reports/rolling_windows.md)         |
| `alt_pickers`                                 | Margin-buffer #1 (5%/10%/20%), the #2, ranks 2–5 equal-weight: the #2 beat the #1 in every window; a 5% buffer cuts switches 39 → 28 at no cost             | [reports/alt_pickers.md](reports/alt_pickers.md)                 |
| `fundamentals_picker`                         | Best revenue-growth + margin rank among the top 10 (SEC XBRL, point-in-time), 2012–2026: matches the #1 on return, modestly better Sharpe                   | [reports/fundamentals_picker.md](reports/fundamentals_picker.md) |
| `rule_variants`                               | Partial trim (once / repeated), stop-and-rebuy on regaining #1, volatility-scaled stop: none beats the plain 25% stop; rebuying ex-leaders costs 0.7–1.3 pp | [reports/rule_variants.md](reports/rule_variants.md)             |
| `breadth`                                     | #1 vs top-3 / top-10 / top-20 equal-weight on complete-data windows: returns peak at three names, Sharpe plateaus from three names on                       | [reports/breadth.md](reports/breadth.md)                         |
| `cadence`                                     | Monthly DCA and annual lump sum ($2,000/yr per leg) vs quarterly: XIRRs move ≤0.15 pp, every ranking holds                                                  | [reports/cadence.md](reports/cadence.md)                         |
| — (every family)                              | Sharpe, Sortino, downside deviation and max drawdown per leg next to XIRR (`results/<id>/risk.csv`, `results/risk_metrics.csv`)                             | [reports/risk_metrics.md](reports/risk_metrics.md)               |
| —                                             | Phase 1 table corrections, known gaps, data caveats                                                                                                         | [reports/methodology.md](reports/methodology.md)                 |

## What changed my mind

Where the later scenario families overturned or sharpened what I believed after the first report:

1. **"From the mid-1990s the #1 became index-like."** I read the 1995–2026 tie (10.66% vs 10.68%) as the strategy settling into an index-like regime once the shaky pre-1996 data dropped out.
   - The [rolling windows](reports/rolling_windows.md) show no convergence at all. Windows starting in 1996–2008 lag by 2–7 pp, and those starting after 2009 lead by up to 17 pp. The 1995 tie is two regimes cancelling out.
   - The [risk metrics](reports/risk_metrics.md) show the tie was really a loss: 21% vs 15% volatility, a −76% drawdown, and 18 years under water.
2. **"The #1 slot carries a quality or momentum edge."** The first report never asked whether _the largest_ mattered or merely _a very large_ company. It barely does:
   - The [placebo](reports/random_pick_placebo.md) puts the #1 at the 74th percentile of random mega-cap pickers, and below the median on Sharpe.
   - The runner-up did better than the #1 in every window ([alt pickers](reports/alt_pickers.md)), and three names beat one on both return and risk ([breadth](reports/breadth.md)).
3. **"The trailing stop's edge is a tax illusion."** I expected realizing gains at 222 stops to erase its lead. The [tax model](reports/tax_drag.md) shows only about 0.2 pp of drag at 15%/32% (0.34 pp at the top rates): most gains are long-term, and the proceeds keep compounding in the index. What tax does shrink is its margin over the index.
4. **"A smarter stop should beat a fixed one."** Selling half, buying back when the stock regains #1, and scaling the stop to volatility all did no better than the fixed 25% stop ([rule variants](reports/rule_variants.md)). Buying back was actively harmful: each rebuy of a fading ex-leader (IBM 1990, Exxon 2012) lagged the index.
5. **"Fundamentals beat size."** A point-in-time revenue-growth plus margin screen, built from SEC filings, matched the #1 over 2012–2026 rather than beating it ([fundamentals](reports/fundamentals_picker.md)). The best risk-adjusted result in that window came from simply equal-weighting the ten names.
6. **"The COMPLETE top-10 lists are complete."** They weren't: Google was missing from 19 quarters (2008–2014) because its pre-2014 market caps are my own estimates, and the list builder read only vendor rows. Building the top-20 lists exposed it.
   - After the fix, the placebo's verdict on the #1 got weaker (80th → 74th percentile), and top-10 equal-weight improved slightly.
   - The #1 table itself was never affected ([methodology](reports/methodology.md)).

**What did not change.** The headline survived every new test: over 1975–2026, buying and holding the #1 lagged the index by about 2 pp a year, driven by IBM's 1987–93 slide and the AT&T breakup. Cadence, taxes, confidence grades, corporate-action treatments and the margin buffer all leave it within a few tenths of a point.

## Reproduce

```sh
source .venv/bin/activate
python scripts/fetch_sources.py        # automatable sources (incl. `tbill`, the risk-free rate, and `sec`, XBRL fundamentals); `cmc` is required on a fresh clone (scraped data is not committed); `cmc_missing` adds only names new to data/universe.csv
python scripts/cache_prices.py         # Yahoo cache + failure report (results/data_quality/)
python scripts/build_manual_prices.py  # T_OLD, T_CORP, SPX_TR
python scripts/build_top_table.py      # Phase 1 table + transitions
python scripts/check_prices.py         # price sanity checks (results/data_quality/)
python -m sp500bt.run --all            # every scenario family + cross-family summary
python -m sp500bt.run --list           # what has been run (scenarios/index.csv)
python tests/test_backtest.py          # engine reconciles to closed-form valuations
```

Adding a scenario: write `scenarios/<id>.toml` (pickers, rules and corporate-action variants are referenced by name from `sp500bt/registry.py`; post-processing from `sp500bt/analyses.py`), add a row to `scenarios/index.csv`, run `python -m sp500bt.run <id>`, and write `reports/<id>.md`.

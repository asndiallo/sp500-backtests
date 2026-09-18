# Buying the #1 S&P 500 company every quarter, 1975–2026

**Setup.** On every quarter start from 1975-01-01 to 2026-01-01 (205 dates), $500 buys the largest S&P 500 company _as of the previous quarter-end close_ (no lookahead). Another $500 buys the S&P 500 total-return index. Everything is valued at the 2026-01-02 close. XIRRs are solved with `scipy.optimize.brentq` on the actual dated cashflows (`sp500bt/metrics.py`). They replace the old "multiple^(1/years)" approximation, which also ignored the index leg's contributions and the buy-the-dip top-ups.

**Bottom line.**

- **Buying and holding the #1 company underperformed the index:** 9.73% vs 11.87% XIRR, or $2.46M vs $5.51M from the same $102,500.
- **The gap comes entirely from 1975–1995 picks.** Routing only the pre-1996 picks to the index makes the strategy match the index (11.88%). A fresh backtest started on 1995-01-01 confirms it: the #1 stock leg ties the index (10.66% vs 10.68%), and both active rules beat it (see the cross-window comparison below).
- **The conclusion rests on the least certain part of the data, but not on the ambiguous rows within it.** Swapping every LOW-confidence pick for its runner-up moves the result by only −0.04 pp. What drives it is IBM's 1987–93 collapse and the AT&T breakup, not uncertainty about who was #1.

## Headline comparison

| Scenario                           | Window                          | Stock-leg invested | Stock-leg final | Stock-leg XIRR | Index-leg invested | Index-leg final | Index-leg XIRR | Combined final | Combined XIRR |
| ---------------------------------- | ------------------------------- | -----------------: | --------------: | -------------: | -----------------: | --------------: | -------------: | -------------: | ------------: |
| Baseline hold                      | 1975–2026                       |           $102,500 |      $2,460,375 |          9.73% |           $102,500 |      $5,508,523 |         11.87% |     $7,968,898 |        11.02% |
| 25% trailing stop → index          | 1975–2026                       |           $102,500 |      $5,200,079 |         11.72% |           $102,500 |      $5,508,523 |         11.87% |    $10,708,602 |        11.80% |
| Buy the dip −25%/−50%              | 1975–2026                       |           $270,500 |      $5,565,832 |         10.28% |           $102,500 |      $5,508,523 |         11.87% |    $11,074,355 |        11.00% |
| Baseline hold                      | 1995–2026                       |            $62,500 |        $442,341 |         10.66% |            $62,500 |        $444,487 |         10.68% |       $886,828 |        10.67% |
| 25% trailing stop → index          | 1995–2026                       |            $62,500 |        $488,826 |         11.14% |            $62,500 |        $444,487 |         10.68% |       $933,313 |        10.92% |
| Buy the dip −25%/−50%              | 1995–2026                       |           $150,500 |      $1,078,642 |         11.30% |            $62,500 |        $444,487 |         10.68% |     $1,523,129 |        11.10% |
| Top-10 equal-weight, baseline hold | **2006–2026 (from 2006-04-01)** |            $40,000 |        $207,746 |         14.67% |            $40,000 |        $178,311 |         13.41% |       $386,057 |        14.07% |

Source: [`results/scenario_comparison.csv`](results/scenario_comparison.csv). The buy-the-dip "invested" figures include its top-ups. **The top-10 row runs on a different window** (2006-04-01 → 2026-01-02, the only period with complete top-10 lists), so compare it only with its own index leg, not with the 1995–2026 rows.

![XIRR by rule and window](charts/summary/xirr_by_window.png)

## Scenario families

Every scenario ever run is listed in [`scenarios/index.csv`](scenarios/index.csv) (id, window, date added, status, results, report). Each family has one config in `scenarios/`, its outputs in `results/<id>/` and `charts/<id>/`, and a report page:

| Family | What it tests | Report |
|---|---|---|
| `top1_core` | #1 company × baseline hold / 25% trailing stop / buy-the-dip, 1975–2026 and fresh 1995–2026 runs; reconciliation; confidence attribution | [reports/top1_core.md](reports/top1_core.md) |
| `top10_ew` | Top-10 equal-weight vs #1 over 2006–2026 | [reports/top10_ew.md](reports/top10_ew.md) |
| `data_sensitivity`, `corp_action_sensitivity` | Confidence grades, pre-1996 data, AT&T 1984 breakup treatment | [reports/sensitivities.md](reports/sensitivities.md) |
| `random_pick_placebo` | 1,000 random top-10 picks per quarter vs the #1 (2006–2026): the #1 ranks at the 80th percentile | [reports/random_pick_placebo.md](reports/random_pick_placebo.md) |
| — | Phase 1 table corrections, known gaps, data caveats | [reports/methodology.md](reports/methodology.md) |

## Reproduce

```sh
source .venv/bin/activate
python scripts/fetch_sources.py        # automatable sources; `cmc` is required on a fresh clone (scraped data is not committed)
python scripts/cache_prices.py         # Yahoo cache + failure report (results/data_quality/)
python scripts/build_manual_prices.py  # T_OLD, T_CORP, SPX_TR
python scripts/build_top_table.py      # Phase 1 table + transitions
python scripts/check_prices.py         # price sanity checks (results/data_quality/)
python -m sp500bt.run --all            # every scenario family + cross-family summary
python -m sp500bt.run --list           # what has been run (scenarios/index.csv)
python tests/test_backtest.py          # engine reconciles to closed-form valuations
```

Adding a scenario: write `scenarios/<id>.toml` (pickers, rules and corporate-action variants are referenced by name from `sp500bt/registry.py`; post-processing from `sp500bt/analyses.py`), add a row to `scenarios/index.csv`, run `python -m sp500bt.run <id>`, and write `reports/<id>.md`.

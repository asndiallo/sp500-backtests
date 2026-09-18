# Risk-adjusted returns: Sharpe, Sortino, drawdown

[← index](../REPORT.md) · code: [`sp500bt/metrics.py`](../sp500bt/metrics.py), [`sp500bt/risk.py`](../sp500bt/risk.py) · results: [`results/risk_metrics.csv`](../results/risk_metrics.csv) (headline rows), [`results/all_risk.csv`](../results/all_risk.csv) (every run), `results/<family>/risk.csv`

**Question.** XIRR says how much money each rule made, not how rough the ride was. Are the rules that win on XIRR also the ones that win per unit of risk?

## Definitions (parameters in `sp500bt/config.py`)

Every metric is computed per **leg** (stock leg, index leg, combined) from that leg's **time-weighted unit value**: the daily value series with contributions and dip top-ups stripped out, `r_t = (V_t − F_t) / V_{t−1} − 1` (`timeseries.unit_value`). Rule proceeds that move into the index stay inside the stock leg, so a trailing-stop leg's risk includes the index money it moved there.

| Metric                 | Formula                                                                                                                                                              | Parameter                                                   |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Periodic returns       | Unit value sampled at each calendar month-end; the first month is measured from the first valued day; the trailing 1-day stub (2026-01-02) is dropped                | `RISK_FREQ = "ME"`, `RISK_PERIODS_PER_YEAR = 12`            |
| Risk-free rate         | FRED **TB3MS** (3-month T-bill, monthly average, % p.a.), per month `rf_m = (1 + TB3MS/100)^(1/12) − 1`, same month as the return                                    | `RISK_FREE = "tb3ms"` (a float sets a constant annual rate) |
| TWR                    | `∏(1 + r_m)^(12/n) − 1`: geometric annual return of one dollar held throughout                                                                                       |                                                             |
| Volatility             | `std(r_m, ddof=1) × √12`                                                                                                                                             |                                                             |
| **Sharpe**             | `mean(r_m − rf_m) / std(r_m − rf_m, ddof=1) × √12`                                                                                                                   |                                                             |
| **Downside deviation** | `√(mean(min(r_m − rf_m, 0)²)) × √12`, averaged over **all** months (the minimum acceptable return is the T-bill)                                                     | MAR = risk-free                                             |
| **Sortino**            | `12 × mean(r_m − rf_m) / downside deviation`                                                                                                                         |                                                             |
| **Max drawdown**       | `min(NAV / running max(NAV) − 1)` on the **daily** unit value; also the peak and trough dates, the first day the old peak is regained, and the peak-to-recovery time | `metrics.max_drawdown`                                      |

**Why monthly.** Before 1996 the old-AT&T and AT&T Corp series are month-end prints, forward-filled daily. Daily volatility would understate their risk; monthly returns treat every series the same way. Drawdowns use the daily series; a forward-filled month can only make an intra-month drawdown shallower, never deeper.

**How to read them next to XIRR.** XIRR is **dollar-weighted**: a DCA portfolio holds almost nothing in its first years, so late returns dominate. The risk metrics are **time-weighted**: every month counts equally, whether the leg held $500 or $5M. The two can disagree:

- The 1995–2026 baseline has a TWR of 11.71% (above the index's 11.14%), but an XIRR of 10.66% (level with the index's 10.68%). The #1 did best in 1995–2000, when little money was invested, and worst in 2000–09, after most of it had arrived.
- The top-10 row shows the reverse (XIRR 15.00%, TWR 11.53%): its best years came late, when the most money was in.

The Sharpe and Sortino ratios therefore describe the **strategy's** path, not a particular DCA investor's balance.

**Source gap closed.** No risk-free series was cached before this phase. TB3MS was added to `scripts/fetch_sources.py` (`python scripts/fetch_sources.py tbill`), stored in `data/sources/fred_tb3ms.csv`. It is public-domain Federal Reserve data.

## All headline scenarios

| Scenario                                      | Window                      |   XIRR |    TWR | Volatility | Sharpe | Downside dev. | Sortino | Max DD | Peak → trough           | Recovered  | Years underwater |
| --------------------------------------------- | --------------------------- | -----: | -----: | ---------: | -----: | ------------: | ------: | -----: | ----------------------- | ---------- | ---------------- |
| Baseline hold                                 | 1975–2026                   |  9.73% | 10.29% |      16.2% |   0.43 |         10.3% |    0.68 | −56.9% | 1999-07-16 → 2002-10-09 | 2007-07-25 | 8.0              |
| *Index leg*                                   | 1975–2026                   | 11.87% | 12.46% |      15.1% |   0.58 |         10.0% |    0.87 | −55.3% | 2007-10-09 → 2009-03-09 | 2012-04-02 | 4.5              |
| Baseline hold (combined)                      | 1975–2026                   | 11.02% | 11.57% |      14.4% |   0.55 |          9.4% |    0.84 | −49.6% | 2000-04-07 → 2002-10-09 | 2007-01-24 | 6.8              |
| 25% trailing stop → index                     | 1975–2026                   | 11.72% | 12.01% |      14.3% |   0.58 |          9.4% |    0.88 | −53.2% | 2007-10-09 → 2009-03-09 | 2012-03-26 | 4.5              |
| 25% trailing stop → index (combined)          | 1975–2026                   | 11.80% | 12.25% |      14.4% |   0.59 |          9.5% |    0.89 | −54.3% | 2007-10-09 → 2009-03-09 | 2012-03-26 | 4.5              |
| Buy the dip −25%/−50%                         | 1975–2026                   | 10.28% | 10.62% |      18.1% |   0.42 |         11.4% |    0.67 | −57.8% | 1999-07-16 → 2002-10-09 | 2008-05-14 | 8.8              |
| Buy the dip −25%/−50% (combined)              | 1975–2026                   | 11.00% | 11.56% |      15.5% |   0.52 |         10.0% |    0.80 | −52.3% | 1999-07-16 → 2002-10-09 | 2007-05-16 | 7.8              |
| Baseline hold                                 | 1995–2026                   | 10.66% | 11.71% |      21.2% |   0.52 |         13.5% |    0.82 | −76.4% | 2000-08-28 → 2009-03-05 | 2018-10-03 | 18.1             |
| *Index leg*                                   | 1995–2026                   | 10.68% | 11.14% |      15.1% |   0.62 |         10.2% |    0.92 | −55.3% | 2007-10-09 → 2009-03-09 | 2012-04-02 | 4.5              |
| Baseline hold (combined)                      | 1995–2026                   | 10.67% | 11.53% |      17.3% |   0.59 |         11.3% |    0.90 | −64.9% | 2000-08-28 → 2009-03-05 | 2013-10-18 | 13.1             |
| 25% trailing stop → index                     | 1995–2026                   | 11.14% | 12.96% |      17.1% |   0.67 |         10.5% |    1.08 | −53.2% | 2007-10-09 → 2009-03-05 | 2012-09-07 | 4.9              |
| 25% trailing stop → index (combined)          | 1995–2026                   | 10.92% | 12.16% |      15.8% |   0.66 |         10.2% |    1.02 | −54.1% | 2007-10-09 → 2009-03-09 | 2012-09-06 | 4.9              |
| Buy the dip −25%/−50%                         | 1995–2026                   | 11.30% | 12.14% |      21.4% |   0.54 |         13.6% |    0.84 | −76.8% | 2000-08-28 → 2009-03-05 | 2015-11-11 | 15.2             |
| Buy the dip −25%/−50% (combined)              | 1995–2026                   | 11.10% | 11.63% |      18.2% |   0.57 |         11.9% |    0.88 | −68.9% | 2000-08-28 → 2009-03-05 | 2013-11-06 | 13.2             |
| Top-10 equal-weight, baseline hold            | 2006–2026 (from 2006-04-01) | 15.00% | 11.53% |      14.2% |   0.73 |          9.3% |    1.12 | −51.3% | 2007-10-09 → 2009-03-09 | 2012-09-13 | 4.9              |
| *Index leg*                                   | 2006–2026 (from 2006-04-01) | 13.41% | 10.91% |      15.2% |   0.66 |         10.2% |    0.98 | −55.3% | 2007-10-09 → 2009-03-09 | 2012-04-02 | 4.5              |
| Top-10 equal-weight, baseline hold (combined) | 2006–2026 (from 2006-04-01) | 14.25% | 11.27% |      14.5% |   0.71 |          9.6% |    1.06 | −53.3% | 2007-10-09 → 2009-03-09 | 2012-09-06 | 4.9              |

"Years underwater" = peak to the first day the unit value regains that peak. The stock leg's drawdown is of the time-weighted unit value; in dollars, new contributions mask part of it.

## What the risk view adds

- **1975–2026: risk does not rescue the #1.**
  - Baseline hold (Sharpe 0.43) and buy-the-dip (0.42) trail the index (0.58) on return and on risk alike.
  - Their worst fall was the 1999–2002 tech/GE slide (−57%/−58%), with 8–9 years underwater.
  - The trailing stop is level with the index (0.575 vs 0.582, Sortino 0.88 vs 0.87): each stop moved a lot into the index, so over time the leg increasingly held the index itself.
- **1995–2026: the XIRR tie is a risk loss.**
  - The baseline and the index both earn about 10.7%, but the #1 had 21% volatility vs 15%, a −76% drawdown vs −55%, and took 18.1 years to regain its 2000 peak.
  - Buy-the-dip's +0.6 pp XIRR edge also comes with a Sharpe below the index (0.54 vs 0.62).
  - **The trailing stop is the only rule that beats the index on both counts** (Sharpe 0.67 vs 0.62, Sortino 1.08 vs 0.92), because it cut the 2000–09 fall from −76% to −53%.
- **2006–2026: top-10 equal-weight beats the index on Sharpe** (0.73 vs 0.66), with a shallower worst drawdown (−51% vs −55%).
- **Placebo, 2006–2026.** The #1 picker ranks at the 74th percentile on XIRR among 1,000 random top-10 picks, but only **38th on Sharpe**. The extra return is extra risk, not skill ([placebo](random_pick_placebo.md)).
- **Rolling windows.** The #1 had a lower Sharpe than the index in 78%, 90% and 99% of the 10-, 15- and 20-year windows. Only 1 of 125 twenty-year windows came out ahead on Sharpe, even in eras where the XIRR spread was large and positive ([rolling windows](rolling_windows.md)).
- **Tax.** Interim tax lowers the trailing stop's Sharpe by about 0.02 and changes no Sharpe ranking ([tax drag](tax_drag.md)).

**Bottom line of the risk view.** Every XIRR advantage the #1 strategy shows over the index comes with proportionally more volatility and deeper drawdowns. Per unit of risk, owning the single largest company has not beaten owning the index over any long horizon in this sample. The exception is the trailing-stop variant, whose risk profile converges on the index because the rule keeps moving money into it.

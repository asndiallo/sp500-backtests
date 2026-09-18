# Contribution cadence: monthly DCA and annual lump sum vs quarterly

[← index](../REPORT.md) · config: [`scenarios/cadence.toml`](../scenarios/cadence.toml) · results: [`results/cadence/`](../results/cadence/)

**Question.** Is anything in the results an artefact of contributing quarterly? Would contributing monthly, or once a year as a lump sum, change the picture?

**Normalization: the same $2,000 per leg per year in every cadence.**

| Cadence | Amount per leg | Contributions, 1975–2026 | Invested per leg |
|---|---:|---:|---:|
| Quarterly (top1_core reference) | $500 each quarter start | 205 | $102,500 |
| Monthly (`freq = "MS"`) | $166.67 (= 2,000 / 12) each month start | 613 | $102,166.67 |
| Annual lump sum (`freq = "YS"`) | $2,000 each January 1 | 52 | $104,000 |

- Every cadence's last contribution is on 2026-01-01, and everything is valued at the 2026-01-02 close.
- The small differences in total invested don't bias the comparison, because XIRR is computed on the actual dated flows.
- Buy-the-dip top-ups equal the triggering lot's purchase ($166.67, $500 or $2,000), so its extra capital scales the same way.
- **The pick** is always the table's #1 as of the previous quarter-end (`row_on`). A monthly contributor buys the same company for all three months of a quarter, and a lump sum buys the #1 observed at the prior December 31.
- **Rules are checked quarterly in every cadence** (`check_freq = "QS"`), so only the contribution timing differs. A sensitivity also checks rules monthly with monthly contributions.

Risk columns: monthly Sharpe vs 3-month T-bills and daily max drawdown of the stock leg's unit value ([definitions](risk_metrics.md)).

## 1975–2026

| Rule | Cadence | Invested (stock leg) | Stock-leg final | Stock XIRR | Sharpe | Max DD | Index XIRR | Stock − index |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline hold | Quarterly $500 *(top1_core)* | $102,500 | $2,460,375 | 9.73% | 0.43 | −57% | 11.87% | −2.15 pp |
| Baseline hold | Monthly $166.67 | $102,167 | $2,447,952 | 9.74% | 0.43 | −57% | 11.86% | −2.12 pp |
| Baseline hold | Annual lump sum $2,000 | $104,000 | $2,482,605 | 9.66% | 0.41 | −56% | 11.93% | −2.27 pp |
| Trailing stop 25% | Quarterly $500 *(top1_core)* | $102,500 | $5,200,079 | 11.72% | 0.58 | −53% | 11.87% | −0.15 pp |
| Trailing stop 25% | Monthly $166.67 | $102,167 | $5,156,382 | 11.72% | 0.58 | −53% | 11.86% | −0.14 pp |
| Trailing stop 25% | Annual lump sum $2,000 | $104,000 | $5,217,310 | 11.62% | 0.57 | −53% | 11.93% | −0.31 pp |
| Trailing stop 25% | Monthly, rules checked monthly | $102,167 | $5,296,466 | 11.79% | 0.57 | −53% | 11.86% | −0.07 pp |
| Buy the dip | Quarterly $500 *(top1_core)* | $270,500 | $5,565,832 | 10.28% | 0.42 | −58% | 11.87% | −1.59 pp |
| Buy the dip | Monthly $166.67 | $269,500 | $5,540,709 | 10.28% | 0.42 | −58% | 11.86% | −1.57 pp |
| Buy the dip | Annual lump sum $2,000 | $274,000 | $6,022,637 | 10.31% | 0.39 | −58% | 11.93% | −1.61 pp |
| Buy the dip | Monthly, rules checked monthly | $271,333 | $5,459,723 | 10.20% | 0.42 | −58% | 11.86% | −1.66 pp |

## 1995–2026 (fresh runs)

| Rule | Cadence | Invested (stock leg) | Stock-leg final | Stock XIRR | Sharpe | Max DD | Index XIRR | Stock − index |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline hold | Quarterly $500 *(top1_core)* | $62,500 | $442,341 | 10.66% | 0.52 | −76% | 10.68% | −0.02 pp |
| Baseline hold | Monthly $166.67 | $62,167 | $441,853 | 10.70% | 0.52 | −76% | 10.67% | +0.03 pp |
| Baseline hold | Annual lump sum $2,000 | $64,000 | $456,355 | 10.61% | 0.51 | −78% | 10.69% | −0.08 pp |
| Trailing stop 25% | Quarterly $500 *(top1_core)* | $62,500 | $488,826 | 11.14% | 0.67 | −53% | 10.68% | +0.46 pp |
| Trailing stop 25% | Monthly $166.67 | $62,167 | $480,201 | 11.10% | 0.67 | −53% | 10.67% | +0.43 pp |
| Trailing stop 25% | Annual lump sum $2,000 | $64,000 | $525,426 | 11.29% | 0.67 | −54% | 10.69% | +0.60 pp |
| Trailing stop 25% | Monthly, rules checked monthly | $62,167 | $508,181 | 11.38% | 0.68 | −53% | 10.67% | +0.71 pp |
| Buy the dip | Quarterly $500 *(top1_core)* | $150,500 | $1,078,642 | 11.30% | 0.54 | −77% | 10.68% | +0.62 pp |
| Buy the dip | Monthly $166.67 | $149,500 | $1,071,369 | 11.33% | 0.54 | −77% | 10.67% | +0.66 pp |
| Buy the dip | Annual lump sum $2,000 | $154,000 | $1,105,257 | 11.23% | 0.53 | −78% | 10.69% | +0.54 pp |
| Buy the dip | Monthly, rules checked monthly | $151,333 | $1,102,498 | 11.31% | 0.53 | −77% | 10.67% | +0.64 pp |
## What this says

**Cadence is not a factor.**
- **XIRR.** Monthly contributions move every XIRR by at most 0.04 pp from quarterly. The annual lump sum moves results by −0.10 to +0.15 pp.
- **Stock minus index.** The spread, which is what the report's conclusions rest on, changes by at most 0.16 pp across cadences.
- **Rankings.** Every ranking in [top1_core](top1_core.md) is preserved: over 1975–2026 the index beats all three rules, and over 1995–2026 the baseline ties the index while both active rules beat it.

**Lump sum vs DCA.**
- **XIRR.** Investing the year's $2,000 on January 1 instead of spreading it lowers the #1 baseline's XIRR slightly (9.66% vs 9.73%) and raises the index's (11.93% vs 11.87%). The index's upward drift rewards earlier investment; the #1's more volatile path doesn't reliably.
- **Dollars.** Final values are higher for the lump sum because it invests $1,500 more per leg and invests each year's money earlier.

**Checking the trailing stop monthly helps it slightly.** +0.07 pp over 1975–2026 and +0.24 pp over 1995–2026: stops fire closer to the 25% line instead of after up to three more months of decline. It does not change its standing relative to the index over 1975–2026 (still 0.07 pp behind).

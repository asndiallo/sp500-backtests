# Rule variants: partial trim, stop-and-rebuy, volatility-scaled stop

[← index](../REPORT.md) · config: [`scenarios/rule_variants.toml`](../scenarios/rule_variants.toml) · results: [`results/rule_variants/`](../results/rule_variants/) (`runs.csv`, `risk.csv`, `event_counts.csv`, `events/`)

**Question.** The fixed 25% trailing stop was the only rule that kept pace with the index on a risk-adjusted basis ([risk metrics](risk_metrics.md)). Do softer, smarter or adaptive versions of it do better?

Every run uses the #1 picker and $500/quarter per leg. Rules are checked quarterly, on the contribution dates, per lot, with the peak measured since purchase. Proceeds from any sale move to the index and stay in the stock leg. Parameters (all in the config):

- **Partial trim** (`partial_trim`: `drop = 0.25`, `fraction = 0.5`).
  - The first time a lot is 25% below its peak, half of its remaining shares are sold into the index; the rest is held.
  - **Main case: one trim per lot** (`max_trims = 1`). Its 222 trims in 1975–2026 fire at exactly the dates and lots where the fixed stop sold everything, so the comparison isolates "sell half" vs "sell all".
  - **Sensitivity: repeated trims** (`max_trims = 99`). After each trim the peak resets to the trim price, so every further 25% fall from the post-trim high sells half of what is left.
- **Stop-and-rebuy** (fixed 25% trailing stop plus the run-level `rebuy` option).
  - The index units bought with a stopped lot's proceeds are switched back into that stock at the first quarterly check on which it is the table's #1 again.
  - That is only allowed after it has been displaced from #1, at the stop date or a later check (`require_loss_of_top = true`).
  - The rebought lot is a new lot with a fresh peak, so it can be stopped again. No new money is involved; the ledger is unchanged.
  - Sensitivity: `require_loss_of_top = false`, which rebuys at the next check where the stock is #1 even if it never lost the top spot.
  - Stocks that stop existing (old AT&T, AT&T Corp) are never rebought. Stop-and-rebuy is not combined with the tax model.
- **Volatility-scaled stop** (`vol_scaled_stop`).
  - **Formula:** `stop_t = clip(k × σ_t, 10%, 50%)`, where `σ_t` is the annualized standard deviation (×√12) of the stock's monthly total returns over the **36 completed months** before the check date. Sell when `price ≤ peak × (1 − stop_t)`.
  - Monthly returns because the pre-1996 AT&T series are month-end prints.
  - **k = 1.0** is the main case. For the quarter's #1, `stop_t` then has a median of 20.6% (interquartile range 17–27%), close to the fixed 25%. k = 1.5 gives a median of 31%.
  - With fewer than 12 months of history the 50% cap applies. This happens in 5 early quarters (old AT&T's series starts in 1974).

Risk columns: monthly Sharpe and Sortino vs 3-month T-bills, and daily max drawdown of the stock leg's unit value ([definitions](risk_metrics.md)). The top1_core rows are the reference runs, unchanged.

## 1975–2026

| Rule | Stock-leg final | XIRR | Sharpe | Sortino | Max DD | Stops / trims | Rebuys (amount) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline hold *(top1_core)* | $2,460,375 | 9.73% | 0.43 | 0.68 | −57% | — | — |
| Fixed 25% trailing stop *(top1_core)* | $5,200,079 | 11.72% | 0.58 | 0.88 | −53% | 222 | — |
| Partial trim: sell 50% at −25%, once per lot | $3,830,227 | 10.91% | 0.53 | 0.82 | −51% | 222 | — |
| Partial trim, repeated | $4,310,895 | 11.22% | 0.55 | 0.83 | −52% | 1213 | — |
| 25% stop + rebuy on regaining #1 | $3,184,550 | 10.42% | 0.49 | 0.74 | −53% | 385 | 214 ($343,825) |
| 25% stop + rebuy whenever #1 (no loss of top required) | $2,937,174 | 10.20% | 0.48 | 0.72 | −53% | 406 | 235 ($325,115) |
| Vol-scaled stop, k = 1.0 | $4,887,831 | 11.56% | 0.56 | 0.84 | −55% | 201 | — |
| Vol-scaled stop, k = 1.5 | $3,554,688 | 10.71% | 0.50 | 0.75 | −55% | 181 | — |
| *Index leg* | $5,508,523 | *11.87%* | *0.58* | *0.87* | *−55%* | | |

## 1995–2026 (fresh runs)

| Rule | Stock-leg final | XIRR | Sharpe | Sortino | Max DD | Stops / trims | Rebuys (amount) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline hold *(top1_core)* | $442,341 | 10.66% | 0.52 | 0.82 | −76% | — | — |
| Fixed 25% trailing stop *(top1_core)* | $488,826 | 11.14% | 0.67 | 1.08 | −53% | 110 | — |
| Partial trim: sell 50% at −25%, once per lot | $465,584 | 10.91% | 0.61 | 0.97 | −64% | 110 | — |
| Partial trim, repeated | $479,853 | 11.05% | 0.64 | 1.03 | −58% | 470 | — |
| 25% stop + rebuy on regaining #1 | $419,819 | 10.40% | 0.60 | 0.96 | −61% | 194 | 135 ($209,084) |
| 25% stop + rebuy whenever #1 (no loss of top required) | $375,870 | 9.86% | 0.54 | 0.86 | −69% | 211 | 152 ($202,826) |
| Vol-scaled stop, k = 1.0 | $516,393 | 11.41% | 0.67 | 1.08 | −53% | 101 | — |
| Vol-scaled stop, k = 1.5 | $544,189 | 11.66% | 0.64 | 1.03 | −61% | 69 | — |
| *Index leg* | $444,487 | *10.68%* | *0.62* | *0.92* | *−55%* | | |
## What this says

**Partial trim is a halfway house, and lands halfway.**
- **1975–2026.** Selling half at the same 222 triggers gives 10.91% XIRR, between baseline hold (9.73%) and the full stop (11.72%), with a Sharpe of 0.53 between 0.43 and 0.58.
- **1995–2026.** Keeping half of each lot keeps half of the 2000–09 damage, so the worst drawdown is −64% vs −53% for the full stop.
- **Repeated trims** move it further toward the full stop (11.22% / 11.05%), because repeated halvings end up selling most of a lot that keeps falling.
- **Verdict.** The value of the trailing stop lies in getting fully out of a fading ex-leader. Holding half back dilutes it.

**Stop-and-rebuy is worse than stopping for good.** It lowers XIRR by 1.3 pp over 1975–2026 (10.42% vs 11.72%) and by 0.74 pp over 1995–2026 (10.40% vs 11.14%), and gives up most of the stop's Sharpe advantage.
- **The costly rebuys** went back into fading ex-leaders the moment they briefly retook #1. Each rebought lot, valued when it was next stopped out, vs the same money left in the index:

  | Rebuy | Amount | Value at next exit | Left in the index |
  |---|---:|---:|---:|
  | IBM, 1990 | $49.9k | $27.2k (1993) | $70.0k |
  | AT&T Corp, 1993 | $13.3k | $17.4k (2000) | $49.7k |
  | GE, 2002 | $28.4k | $34.6k (2008) | $47.8k |
  | Exxon, 2012 | $61.7k | $36.4k (2020) | $144.0k |

  Only the 2013–2020 Apple and Microsoft rebuys beat the index.
- **Regaining the top spot after a 25% fall is not a recovery signal.** Among these giants it more often meant the challenger had stumbled.
- **Without the "must have lost #1" condition** it is worse still (10.20% / 9.86%): it rebuys a stock that is still #1 right after stopping out of it.

**The volatility-scaled stop is about as good as the fixed stop, not better.**
- **k = 1.0:** 11.56% vs 11.72% over 1975–2026, and 11.41% vs 11.14% over 1995–2026. Sharpe is essentially equal (0.56 vs 0.58; 0.67 vs 0.67).
- **k = 1.5:** the wider stops lag badly over 1975–2026 (10.71%), because they let IBM and old-AT&T lots fall further before selling. They help over 1995–2026 (11.66%) by not stopping out of Apple and Microsoft in shallow dips, but at the cost of a −61% drawdown.
- **Verdict.** Adapting the distance to volatility neither adds nor removes an edge. The fixed 25% is as defensible as any volatility-tuned width, and it has one fewer parameter.

# Tax drag on the three rules

[← index](../REPORT.md) · config: [`scenarios/tax_drag.toml`](../scenarios/tax_drag.toml) · results: [`results/tax_drag/tax_comparison.csv`](../results/tax_drag/tax_comparison.csv)

**Question.** The trailing stop realizes a taxable gain at each of its 222 triggers, while baseline hold defers almost everything to the end. Does the ranking between rules change once capital-gains tax is included?

**Model (all parameters in the config).**

The rates are **illustrative assumptions, not personalized tax advice**:

- **Base case:** 15% long-term (held more than 365 days), 32% short-term.
- **Sensitivity:** 23.8% / 40.8%, the top US federal rates including the 3.8% net investment income tax.

How realizations are handled:

- **Sales.** Tax is due on every trailing-stop sale and on corporate-action cash (the SBC deal's $1.30/share). It is paid out of the proceeds, and only the after-tax amount moves to the index.
- **Reorganizations are tax-free.** The 1984 AT&T breakup and the stock part of the SBC merger split cost basis by value, and the original acquisition date carries over.
- **Losses.** Realized losses go into a carryforward that offsets later gains. Some stops do sell below cost: $9,801 of losses over 1975–2026 under the base rates.
- **Accounts.** Each leg is its own taxable account.

Final values are shown **both ways**:

1. _Interim tax only_: pre-liquidation, the account is still invested on 2026-01-02.
2. _After liquidation_: tax on all unrealized gains at the 2026-01-02 close is also deducted, for the index leg too.

**Not modelled:** tax on dividends, in every leg alike. All price series reinvest dividends pre-tax, which flatters high-yield holdings (old AT&T, and the index in the 1970s–80s) relative to a real taxable account.

**Does buy-the-dip ever sell? No.** It is pure accumulation: its event log contains only top-ups and corporate actions. Its only realizations are the SBC deal's $1.30 cash on 54 AT&T-lineage lots ($115 of tax in total). That is a _structural_ tax advantage over the trailing stop, not an omission. Baseline hold is the same apart from 18 such lots ($103).

## 1975–2026 (base rates 15% / 32%)

| Rule              | Pre-tax XIRR | After interim tax | After liquidation | Sharpe pre-tax | Sharpe after interim tax | Interim tax paid | Realizations | Liquidation tax |
| ----------------- | -----------: | ----------------: | ----------------: | -------------: | -----------------------: | ---------------: | -----------: | --------------: |
| Baseline hold     |        9.73% |             9.73% |             9.31% |           0.43 |                     0.43 |             $103 |           18 |        $353,505 |
| 25% trailing stop |       11.72% |            11.51% |            11.11% |           0.58 |                     0.56 |          $36,240 |          222 |        $674,984 |
| Buy the dip       |       10.28% |            10.28% |             9.83% |           0.42 |                     0.42 |             $115 |           54 |        $794,094 |
| _Index leg_       |     _11.87%_ |          _11.87%_ |          _11.45%_ |         _0.58_ |                   _0.58_ |               $0 |            0 |        $810,935 |

## 1995–2026 (base rates, fresh runs)

| Rule              | Pre-tax XIRR | After interim tax | After liquidation | Sharpe pre-tax | Sharpe after interim tax | Interim tax paid | Realizations |
| ----------------- | -----------: | ----------------: | ----------------: | -------------: | -----------------------: | ---------------: | -----------: |
| Baseline hold     |       10.66% |            10.66% |             9.98% |           0.52 |                     0.52 |               $0 |            0 |
| 25% trailing stop |       11.14% |            10.89% |            10.25% |           0.67 |                     0.65 |           $3,126 |          110 |
| Buy the dip       |       11.30% |            11.30% |            10.58% |           0.54 |                     0.54 |               $0 |            0 |
| _Index leg_       |     _10.68%_ |          _10.68%_ |          _10.00%_ |         _0.62_ |                   _0.62_ |               $0 |            0 |

## Rate sensitivity, 1975–2026 (23.8% / 40.8%)

| Rule              |  Pre-tax | After interim tax | After liquidation | Sharpe pre-tax | Sharpe after interim tax |
| ----------------- | -------: | ----------------: | ----------------: | -------------: | -----------------------: |
| Baseline hold     |    9.73% |             9.73% |             9.03% |           0.43 |                     0.43 |
| 25% trailing stop |   11.72% |            11.38% |            10.71% |           0.58 |                     0.55 |
| Buy the dip       |   10.28% |            10.28% |             9.52% |           0.42 |                     0.42 |
| _Index leg_       | _11.87%_ |          _11.87%_ |          _11.17%_ |         _0.58_ |                   _0.58_ |

Sharpe ratios are on the monthly unit value ([risk metrics](risk_metrics.md)). Tax paid out of stop proceeds is a loss to the account, not a withdrawal, so interim tax lowers the path too. Liquidation tax is a single terminal deduction and has no Sharpe counterpart. Interim tax also deepens the 1995–2026 trailing stop's max drawdown from −53% to −56%.

**Does the ranking change? No, in every case.**

- **1975–2026:** trailing stop > buy-the-dip > baseline, pre-tax, after interim tax and after liquidation, at both rate levels.
- **1995–2026:** buy-the-dip > trailing stop > baseline, in every tax treatment.
- **On Sharpe**, the trailing stop stays first in both windows after interim tax (0.56 vs 0.43/0.42 over 1975–2026; 0.65 vs 0.54/0.52 over 1995–2026). In 1995–2026 it still beats the index's 0.62 after tax.

**Why the drag is small.** The trailing stop's tax costs 0.21 pp at base rates (0.34 pp at the high rates), because:

- most of its gains are long-term;
- the proceeds keep compounding in the index;
- the baseline eventually pays its deferred tax at liquidation.

The deferral advantage therefore buys only the time value on about $36k of tax paid early, against a $5M account.

**What tax does change is the comparison with the index.**

- **1975–2026:** after liquidation, the trailing stop trails the index by 0.34 pp (11.11% vs 11.45%), up from 0.15 pp pre-tax.
- **1995–2026:** its lead over the index shrinks from +0.46 to +0.25 pp.
- **1995–2026 baseline tie survives tax:** 9.98% vs 10.00% after liquidation.

"""Illustrative capital-gains tax model (not tax advice).

* Realized gains are taxed when a lot is sold (trailing stop) or converted to cash
  in a corporate action: long-term rate if held more than ``lt_days`` days, else the
  short-term rate. Stock-for-stock reorganisations are tax-free: basis is split by
  value across the new lots and the acquisition date carries over.
* Realized losses go into a carryforward that offsets later gains (no annual
  ordinary-income offset). At liquidation, short- and long-term results are netted
  against each other first, roughly as US rules do.
* Each leg is its own account (its own carryforward), so the stock leg and the
  index leg stay comparable.
* Dividends are NOT taxed: every adjusted-price series reinvests dividends pre-tax,
  for every leg alike.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class TaxModel:
    lt_rate: float
    st_rate: float
    lt_days: int = 365
    carryforward: dict = field(default_factory=dict)   # leg -> unused realized losses ($)
    paid: dict = field(default_factory=dict)           # leg -> tax paid on interim realizations ($)
    realized: list = field(default_factory=list)       # audit trail

    @classmethod
    def from_config(cls, cfg: dict | None) -> TaxModel | None:
        if not cfg:
            return None
        return cls(lt_rate=cfg["lt_rate"], st_rate=cfg["st_rate"], lt_days=cfg.get("lt_days", 365))

    def is_long_term(self, acquired, sold) -> bool:
        return (pd.Timestamp(sold) - pd.Timestamp(acquired)).days > self.lt_days

    def on_sale(self, leg: str, date, proceeds: float, basis: float, acquired) -> float:
        """Tax due on one realization (0 for a loss, which is carried forward)."""
        gain = proceeds - basis
        lt = self.is_long_term(acquired, date)
        carry = self.carryforward.get(leg, 0.0)
        if gain <= 0:
            self.carryforward[leg] = carry - gain
            tax = 0.0
        else:
            used = min(carry, gain)
            self.carryforward[leg] = carry - used
            tax = (gain - used) * (self.lt_rate if lt else self.st_rate)
        self.paid[leg] = self.paid.get(leg, 0.0) + tax
        self.realized.append((pd.Timestamp(date), leg, proceeds, basis, gain, lt, tax))
        return tax

    def liquidation_tax(self, leg: str, date, positions: list[tuple[float, float, object]]) -> float:
        """Tax if every (value, basis, acquired) position of ``leg`` were sold on ``date``.
        Does not mutate state."""
        st = sum(v - b for v, b, a in positions if not self.is_long_term(a, date))
        lt = sum(v - b for v, b, a in positions if self.is_long_term(a, date))
        if st < 0:
            lt, st = lt + st, 0.0
        elif lt < 0:
            st, lt = st + lt, 0.0
        carry = self.carryforward.get(leg, 0.0)
        use = min(carry, max(st, 0.0))
        st, carry = st - use, carry - use
        lt -= min(carry, max(lt, 0.0))
        return max(st, 0.0) * self.st_rate + max(lt, 0.0) * self.lt_rate

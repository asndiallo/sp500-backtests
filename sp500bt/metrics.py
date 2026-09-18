"""Money-weighted return metrics on dated cashflows."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq


def xnpv(rate: float, flows: pd.Series) -> float:
    t0 = flows.index[0]
    years = (flows.index - t0).days / 365.25
    return float(np.sum(flows.values / (1.0 + rate) ** years))


def xirr(flows: pd.Series) -> float:
    """Annualised internal rate of return for irregular dated cashflows.

    ``flows`` is indexed by date; contributions negative, terminal value positive.
    Solved with Brent's method on [-99%, +1000%]."""
    flows = flows.groupby(level=0).sum().sort_index()
    if not ((flows < 0).any() and (flows > 0).any()):
        raise ValueError("xirr needs at least one negative and one positive cashflow")
    return brentq(lambda r: xnpv(r, flows), -0.99, 10.0, xtol=1e-10, maxiter=500)

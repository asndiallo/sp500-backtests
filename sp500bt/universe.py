"""Company universe: ticker <-> names <-> companiesmarketcap slug <-> S&P 500 add date."""
from __future__ import annotations

import pandas as pd

from .config import DATA_DIR

UNIVERSE_CSV = DATA_DIR / "universe.csv"


def load_universe() -> pd.DataFrame:
    u = pd.read_csv(UNIVERSE_CSV, parse_dates=["sp500_added"])
    u["aliases"] = u["aliases"].fillna("").str.split("|")
    return u


def name_to_ticker(name: str, universe: pd.DataFrame | None = None) -> str | None:
    """Map a company name as printed by a source (FT/Wikipedia/MS) to our ticker."""
    u = load_universe() if universe is None else universe
    key = name.strip().lower()
    for r in u.itertuples():
        if any(key == a.strip().lower() for a in r.aliases if a):
            return r.ticker
    return None


def in_sp500(ticker: str, date, universe: pd.DataFrame | None = None) -> bool:
    u = load_universe() if universe is None else universe
    row = u[u.ticker == ticker]
    return bool(len(row)) and pd.Timestamp(date) >= row.iloc[0].sp500_added

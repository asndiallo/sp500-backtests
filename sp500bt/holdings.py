"""Phase 1 table access and the pickers that turn it into buy decisions."""
from __future__ import annotations

import pandas as pd

from .config import TOP_HOLDINGS_CSV


def load_top_holdings(path=TOP_HOLDINGS_CSV) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)


def row_on(date, holdings: pd.DataFrame) -> pd.Series:
    """Latest table row effective on or before ``date`` (point-in-time)."""
    sub = holdings[holdings["date"] <= pd.Timestamp(date)]
    if sub.empty:
        raise ValueError(f"no Phase 1 row on or before {pd.Timestamp(date).date()}")
    return sub.iloc[-1]


def top1_picker(date, holdings):
    row = row_on(date, holdings)
    return row, [(row["top1_ticker"], 1.0)]


def top1_alt_picker(date, holdings):
    """Sensitivity: use ``alt_top1_ticker`` wherever the row is LOW confidence."""
    row = row_on(date, holdings)
    t = row["alt_top1_ticker"] if row["confidence"] == "LOW" and isinstance(row["alt_top1_ticker"], str) \
        else row["top1_ticker"]
    return row, [(t, 1.0)]


def make_confidence_gate(allowed: set[str], fallback: str):
    """Sensitivity: buy the #1 only on rows whose confidence is in ``allowed``;
    otherwise put the stock-leg money into ``fallback`` (e.g. the index)."""
    def picker(date, holdings):
        row = row_on(date, holdings)
        return row, [(row["top1_ticker"] if row["confidence"] in allowed else fallback, 1.0)]
    return picker


def top10_picker(date, holdings):
    row = row_on(date, holdings)
    if row["top10_status"] != "COMPLETE":
        raise ValueError(f"top-10 list for {row['date'].date()} is {row['top10_status']}; "
                         "run the top-10 variant only over the COMPLETE window")
    tickers = row["top10_tickers"].split(",")
    return row, [(t, 1.0 / len(tickers)) for t in tickers]

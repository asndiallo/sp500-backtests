"""Corporate actions: load data/corporate_actions.csv and convert lots through them.

Schema (extends the notebook's original one):
    old_ticker, event_date, mode, cash_per_share, new_ticker, ratio, notes, source_url

Modes
    cash          lot -> cash_per_share per real share; proceeds go to the index leg
    stock         lot -> ``ratio`` real shares of new_ticker per real old share
    value_split   lot value split across several rows sharing (old_ticker, event_date);
                  ``ratio`` is the fraction of value going to new_ticker (rows sum to 1)
    bankruptcy    lot value -> 0 (equity cancelled; no bridging to a successor ticker)
    writeoff      sensitivity only: fraction ``ratio`` of the lot's value is lost
                  (counts toward the value_split total)
    yahoo_adjusted / info
                  documentation only: the event is already inside Yahoo's adjusted
                  series (fractional pseudo-split or special dividend) -- no-op here

Conversions are value-based: the lot's dollar value on the event date is computed
from its own total-return series, and the exchange multiplier uses *nominal*
prices (``ratio * P_new / P_old``), so dividend-adjustment factors of the two
series never leak into share counts. For a merger at close the multiplier is ~1.
"""
from __future__ import annotations

import pandas as pd

from .config import CORP_ACTIONS_CSV

ACTIVE_MODES = {"cash", "stock", "value_split", "bankruptcy", "writeoff"}


def load_corporate_actions(path=CORP_ACTIONS_CSV) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["event_date"])
    df["mode"] = df["mode"].str.strip()
    return df.sort_values("event_date").reset_index(drop=True)


def active_events(df: pd.DataFrame) -> dict[str, list[pd.DataFrame]]:
    """{old_ticker: [event-group DataFrame, ...]} in date order, active modes only."""
    out: dict[str, list[pd.DataFrame]] = {}
    act = df[df["mode"].isin(ACTIVE_MODES)]
    for (t, _d), g in act.groupby(["old_ticker", "event_date"], sort=True):
        if (g["mode"] == "value_split").any():
            total = g.loc[g["mode"].isin(["value_split", "writeoff"]), "ratio"].sum()
            if abs(total - 1.0) > 1e-4:
                raise ValueError(f"value_split fractions for {t} on {_d.date()} sum to {total}, not 1")
        out.setdefault(t, []).append(g)
    return out

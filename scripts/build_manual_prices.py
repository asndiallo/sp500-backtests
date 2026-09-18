"""Build the hand-made price series Yahoo does not carry.

Outputs (data/manual_prices/*.csv, columns ``date,close,nominal``; ``close`` is a
total-return level, ``nominal`` the as-traded price when known):

* T_OLD   pre-divestiture AT&T, month-end, 1974-01 .. 1983-12-30
* T_CORP  post-divestiture AT&T Corp, month-end, 1984-01 .. 2005-11-18
* SPX_TR  spliced daily S&P 500 total-return index (see sp500bt.index_tr)

Dividends are credited at the month-end *preceding* the payment date (ex-dates
fell a few weeks before payment); spinoff value is treated as reinvested in the
parent (same convention Yahoo uses for its fractional "splits"), using the IRS
basis-allocation percentages as the value split.

Run:  python scripts/build_manual_prices.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sp500bt import index_tr  # noqa: E402
from sp500bt.config import MANUAL_PRICES_DIR, SOURCES_DIR  # noqa: E402

PRICES = SOURCES_DIR / "att_monthly_prices_historicalstockinfo.csv"
DIVS = SOURCES_DIR / "att_dividends.csv"
EVENTS = SOURCES_DIR / "att_corp_capital_events.csv"


def _monthly_prices() -> pd.Series:
    df = pd.read_csv(PRICES, comment="#", parse_dates=["date"])
    return df.set_index("date")["price"].astype(float)


def _dividends(symbol: str) -> pd.Series:
    d = pd.read_csv(DIVS, parse_dates=["pay_date"])
    d = d[d.symbol == symbol]
    credit = (d.pay_date - pd.offsets.MonthEnd(1))  # month-end before payment
    return d.groupby(credit.values)["amount"].sum()


def _fill_1998(px: pd.Series) -> tuple[pd.Series, list]:
    """The source table skips 1998. Use the ref-sheet prices on 1998 dividend
    dates as anchors and log-interpolate the remaining month-ends."""
    d = pd.read_csv(DIVS, parse_dates=["pay_date"])
    d = d[(d.symbol == "T_CORP") & (d.pay_date.dt.year == 1998)]
    anchors = {r.pay_date: float(r.note.split("price when paid ")[1].split(";")[0]) for r in d.itertuples()}
    months = pd.date_range("1998-01-31", "1998-12-31", freq="ME")
    known = pd.concat([px.loc["1997-10":"1997-12"], pd.Series(anchors), px.loc["1999-01":"1999-02"]]).sort_index()
    grid = known.index.union(months)
    filled = np.exp(np.log(known).reindex(grid).interpolate(method="time"))
    return pd.concat([px, filled.loc[months]]).sort_index(), list(months)


def _tr_from_monthly(px: pd.Series, divs: pd.Series, events: pd.DataFrame | None = None) -> pd.DataFrame:
    """Total-return level per *original* share: value = price * K, where K carries
    splits (share count) and spinoffs (value reinvested) that occurred up to t."""
    K = pd.Series(1.0, index=px.index)
    if events is not None:
        for ev in events.itertuples():
            f = (ev.shares_factor if pd.notna(ev.shares_factor) else 1.0) * \
                (ev.value_factor if pd.notna(ev.value_factor) else 1.0)
            K.loc[K.index >= pd.Timestamp(ev.date)] *= f
    val = px * K
    div_val = divs.reindex(px.index).fillna(0.0) * K
    ret = (val + div_val) / val.shift(1) - 1.0
    tr = (1.0 + ret.fillna(0.0)).cumprod()
    return pd.DataFrame({"close": tr, "nominal": px})


def build_t_old() -> pd.DataFrame:
    px = _monthly_prices().loc["1974-01-01":"1983-12-31"]
    px.index = px.index.where(px.index != pd.Timestamp("1983-12-31"), pd.Timestamp("1983-12-30"))
    return _tr_from_monthly(px, _dividends("T_OLD").rename(lambda d: d if d != pd.Timestamp("1983-12-31")
                                                               else pd.Timestamp("1983-12-30")))


# First regular-way value of new AT&T Corp: 100 shares were worth $1,800 on the
# first business day after divestiture (1984-01-03), per Wollman. It is dated
# 1983-12-30 so the divestiture (effective 1984-01-01) can be valued on one date.
T_CORP_OPEN = (pd.Timestamp("1983-12-30"), 18.00, "https://bimajority.org/~wollman/t.html")


def build_t_corp() -> tuple[pd.DataFrame, list]:
    px = _monthly_prices().loc["1984-01-01":]
    px = pd.concat([pd.Series({T_CORP_OPEN[0]: T_CORP_OPEN[1]}), px])
    px, interpolated = _fill_1998(px)
    ev = pd.read_csv(EVENTS, parse_dates=["date"])
    ev = ev[ev.shares_factor.notna() | ev.value_factor.notna()]
    # a split/spin inside month m affects that month-end's price onward
    ev["date"] = ev["date"] + pd.offsets.MonthEnd(0)
    tr = _tr_from_monthly(px, _dividends("T_CORP"), ev)
    return tr, interpolated


def _write(symbol: str, df: pd.DataFrame, header: str) -> None:
    with open(MANUAL_PRICES_DIR / f"{symbol}.csv", "w") as f:
        f.write(f"# {header}\n")
        df.rename_axis("date").to_csv(f, float_format="%.6f")


def main() -> None:
    t_old = build_t_old()
    _write("T_OLD", t_old, "Pre-divestiture AT&T total-return level (month-end). Prices: data/sources/"
           "att_monthly_prices_historicalstockinfo.csv; dividends: AT&T annual reports 1974-83.")
    t_corp, interp = build_t_corp()
    _write("T_CORP", t_corp, "AT&T Corp 1984-01..2005-11-18 total-return level (month-end); spinoff value "
           "reinvested via IRS basis allocations; first row = $18.00 first regular-way value (Wollman) "
           "dated 1983-12-30; 1998 month-ends log-interpolated between dividend-date prices: "
           + ",".join(d.strftime('%Y-%m') for d in interp))
    index_tr.write_manual_csv()
    for s, df in (("T_OLD", t_old), ("T_CORP", t_corp)):
        yrs = (df.index[-1] - df.index[0]).days / 365.25
        print(f"{s}: {df.index[0].date()}..{df.index[-1].date()} n={len(df)} "
              f"TR CAGR={(df.close.iloc[-1] / df.close.iloc[0]) ** (1 / yrs) - 1:.2%} "
              f"price CAGR={(df.nominal.iloc[-1] / df.nominal.iloc[0]) ** (1 / yrs) - 1:.2%}")
    print("SPX_TR validation vs ^SP500TR:", index_tr.validate())


if __name__ == "__main__":
    main()

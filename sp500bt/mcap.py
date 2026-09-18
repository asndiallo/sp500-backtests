"""Point-in-time market-cap estimates: nominal price x shares outstanding.

Used for the Phase 1 table where no vendor market-cap history exists (1974-1995).
Share counts come from ``data/sources/share_counts.csv`` (annual reports, 10-K /
10-Q covers, contemporaneous earnings stories) plus counts *implied* by the
Business Week / Forbes market values in ``market_value_snapshots.csv``.

Counts are stored as-traded; to interpolate across a stock split every
observation is first expressed in a common (post-2000) split basis, interpolated
linearly in time, then converted back to the as-traded basis of each date.
Beyond the first/last observation the count is held flat and the row is flagged
``extrapolated`` so the Phase 1 table can downgrade its confidence.
"""
from __future__ import annotations

import pandas as pd

from .config import MANUAL_PRICES_DIR, SOURCES_DIR
from .prices import load_yahoo_history, nominal_close

SPLIT_BASIS_CUTOFF = pd.Timestamp("2000-12-31")  # only real splits before this matter here


def manual_nominal(symbol: str) -> pd.Series:
    df = pd.read_csv(MANUAL_PRICES_DIR / f"{symbol}.csv", comment="#", parse_dates=["date"])
    return df.set_index("date")["nominal"].astype(float).rename(symbol)


def nominal_price(symbol: str) -> pd.Series:
    return manual_nominal(symbol) if (MANUAL_PRICES_DIR / f"{symbol}.csv").exists() else nominal_close(symbol)


def _splits(symbol: str) -> pd.Series:
    if (MANUAL_PRICES_DIR / f"{symbol}.csv").exists():
        return pd.Series(dtype=float)  # manual series: counts recorded in as-traded basis, no splits in-window
    s = load_yahoo_history(symbol)["Stock Splits"]
    s = s[(s > 0) & (s.index <= SPLIT_BASIS_CUTOFF)]
    return s


def _factor_after(splits: pd.Series, date: pd.Timestamp) -> float:
    """Product of split ratios strictly after ``date`` (up to the cutoff)."""
    return float(splits[splits.index > date].prod()) if len(splits) else 1.0


def implied_share_counts(tickers=("IBM", "XOM", "GE")) -> pd.DataFrame:
    """Counts implied by published market values. Only for symbols with *daily*
    nominal prices (a month-end series would mis-price mid-month snapshot dates)."""
    snap = pd.read_csv(SOURCES_DIR / "market_value_snapshots.csv", parse_dates=["as_of"])
    rows = []
    for r in snap[snap.ticker.isin(tickers)].itertuples():
        px = nominal_price(r.ticker).loc[:r.as_of].iloc[-1]
        rows.append({"ticker": r.ticker, "date": r.as_of, "shares_millions": r.market_value_billions * 1e3 / px,
                     "basis": "implied", "source_url": r.source_url,
                     "derivation": f"{r.publication}: ${r.market_value_billions}B / nominal close {px:.3f}"})
    return pd.DataFrame(rows)


def share_count_table() -> pd.DataFrame:
    sc = pd.read_csv(SOURCES_DIR / "share_counts.csv", comment="#", parse_dates=["date", "basis_date"])
    imp = implied_share_counts()
    return pd.concat([sc, imp], ignore_index=True).sort_values(["ticker", "date"])


def shares_on(symbol: str, dates: pd.DatetimeIndex, table: pd.DataFrame | None = None) -> pd.DataFrame:
    """As-traded share count (millions) on each date, plus an extrapolation flag."""
    table = share_count_table() if table is None else table
    obs = table[table.ticker == symbol]
    if obs.empty:
        raise KeyError(f"no share-count observations for {symbol}")
    splits = _splits(symbol)
    basis = obs["basis_date"].fillna(obs["date"]) if "basis_date" in obs else obs["date"]
    common = pd.Series([r.shares_millions * _factor_after(splits, b)
                        for r, b in zip(obs.itertuples(), basis, strict=True)],
                       index=obs.date.values).groupby(level=0).mean()
    grid = common.index.union(dates)
    interp = common.reindex(grid).interpolate(method="time").ffill().bfill().reindex(dates)
    as_traded = pd.Series([interp[d] / _factor_after(splits, d) for d in dates], index=dates)
    flag = (dates < common.index.min()) | (dates > common.index.max())
    return pd.DataFrame({"shares_millions": as_traded, "extrapolated": flag}, index=dates)


def market_caps(symbols: list[str], dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Long table: date, ticker, nominal price, shares, market cap ($bn), flags."""
    table = share_count_table()
    out = []
    for s in symbols:
        px = nominal_price(s)
        sh = shares_on(s, dates, table)
        for d in dates:
            sub = px.loc[:d]
            if sub.empty or (d - sub.index[-1]).days > 35:
                continue  # not trading yet / no recent print
            p = float(sub.iloc[-1])
            out.append({"date": d, "ticker": s, "price_date": sub.index[-1], "price": p,
                        "shares_millions": sh.at[d, "shares_millions"],
                        "shares_extrapolated": bool(sh.at[d, "extrapolated"]),
                        "mcap_bn": p * sh.at[d, "shares_millions"] / 1e3})
    return pd.DataFrame(out)

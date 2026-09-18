"""Price layer: yfinance with a local parquet cache, plus hand-built manual series.

Two flavours of price are needed:

* ``adjusted_close`` -- split- *and* dividend-adjusted close, i.e. a total-return
  series. This is what the backtest trades on. It is Yahoo's ``Adj Close``, which
  is numerically identical to ``yf.download(auto_adjust=True)['Close']``
  (verified: max abs diff 0.0 on IBM 1975-2026).
* ``nominal_close`` -- the price as it actually printed on the tape, rebuilt by
  undoing Yahoo's split adjustment. Needed to estimate historical market caps
  (nominal price x shares outstanding) for the Phase 1 table.

Symbols Yahoo does not carry (pre-1984 AT&T, the spliced long-run S&P 500
total-return index, ...) live as CSVs in ``data/manual_prices/<SYMBOL>.csv``
with columns ``date,close`` where ``close`` is already a total-return level.
A manual file always takes precedence over Yahoo for the same symbol.

Stooq fallback: not available. pandas-datareader 0.11 removed its Stooq reader
and stooq.com now gates CSV downloads behind a JavaScript proof-of-work bot
check, which this project does not circumvent. Gaps are surfaced as
``PriceDataError`` instead of being silently dropped.
"""
from __future__ import annotations

import pandas as pd

from .config import CACHE_DIR, MANUAL_PRICES_DIR


class PriceDataError(RuntimeError):
    """Raised when no usable price series exists for a symbol."""


def _cache_path(ticker: str):
    return CACHE_DIR / f"yf_{ticker.replace('.', '_').replace('^', 'IDX_')}.parquet"


def load_yahoo_history(ticker: str, force_refresh: bool = False) -> pd.DataFrame:
    """Full daily history (unadjusted OHLC + Adj Close + Dividends + Stock Splits)."""
    path = _cache_path(ticker)
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)
    import yfinance as yf  # imported lazily so offline runs off the cache work

    df = yf.Ticker(ticker).history(period="max", auto_adjust=False, actions=True)
    if df is None or df.empty:
        raise PriceDataError(
            f"yfinance returned no data for {ticker!r} (delisted, renamed, or never on Yahoo)")
    df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(path)
    return df


def manual_series(symbol: str) -> pd.Series | None:
    path = MANUAL_PRICES_DIR / f"{symbol}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"], comment="#")
    return df.set_index("date")["close"].astype(float).sort_index().rename(symbol)


def adjusted_close(symbol: str) -> pd.Series:
    """Total-return price series for ``symbol`` (manual file first, then Yahoo)."""
    s = manual_series(symbol)
    if s is not None:
        return s
    return load_yahoo_history(symbol)["Adj Close"].rename(symbol)


def nominal_close(ticker: str) -> pd.Series:
    """As-traded close: Yahoo's split-adjusted Close times every later split factor.

    Yahoo encodes some spinoffs as fractional pseudo-splits (e.g. IBM 1.046 on
    2021-11-04 for Kyndryl); they are included on purpose because Yahoo's Close
    was divided by them too, so multiplying back recovers the printed price.
    """
    h = load_yahoo_history(ticker)
    splits = h["Stock Splits"].replace(0, 1.0).fillna(1.0)
    # factor for day t = product of split ratios strictly after t
    later = splits[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
    return (h["Close"] * later).rename(ticker)


def price_on_or_before(series: pd.Series, as_of) -> float:
    """Most recent value on or before ``as_of`` (weekends/holidays roll back)."""
    sub = series.loc[: pd.Timestamp(as_of)]
    if sub.empty:
        raise PriceDataError(f"No {series.name} price on or before {pd.Timestamp(as_of).date()}")
    return float(sub.iloc[-1])

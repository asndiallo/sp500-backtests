"""Phase 3 sanity checks: every price series against at least one independent number.

1. Dated anchors: contemporaneous closes quoted in news / filings (nominal prices).
2. Vendor cross-check (every universe ticker with companiesmarketcap history):
   implied shares = cmc market cap / Yahoo split-adjusted close; a quarter-over-
   quarter jump > 10% must be explained by a real share issue (e.g. a stock-for-
   stock merger) or it flags a price/vendor problem.
3. Yahoo spinoff pseudo-splits vs the documented distribution terms.
4. Manual series (T_OLD / T_CORP) vs independent year-end prints.

Writes results/data_quality/price_sanity.csv and prints anything flagged.
Run:  python scripts/check_prices.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sp500bt.config import DATA_QUALITY_DIR, SOURCES_DIR  # noqa: E402
from sp500bt.mcap import nominal_price  # noqa: E402
from sp500bt.prices import load_yahoo_history  # noqa: E402

# (symbol, date, independent nominal close, tolerance, source)
ANCHORS = [
    ("IBM", "1980-12-31", 67.875, 0.01, "UPI 1981-12-31: IBM 'lost 11 to 56' in 1981 -> 1980 close ~67 7/8"),
    ("IBM", "1981-12-31", 56.875, 0.02,
     "https://www.upi.com/Archives/1981/12/31/Stocks-wind-up-1981-with-a-loss-and-record-volume/1888378622800/"),  # noqa: E501
    ("IBM", "1982-12-31", 96.25, 0.01,
     "https://www.upi.com/Archives/1982/12/31/Stocks-score-best-gain-in-7-years-on-record-volume-in-historic-1982/6401410158800/"),  # noqa: E501
    ("T_OLD", "1981-12-31", 58.75, 0.02,
     "UPI 1981-12-31: AT&T 'up 10 to 58' (58 3/4); HSI series is the last-day high-low average"),
    ("T_OLD", "1983-12-30", 61.50, 0.01, "https://bimajority.org/~wollman/t.html ($6,150 per 100 shares)"),
    ("T_CORP", "1983-12-30", 18.00, 0.001,
     "https://bimajority.org/~wollman/t.html ($1,800 per 100 shares, first business day)"),
    ("XOM", "1994-02-28", 64.875, 0.01, "Exxon 10-K FY1993 cover: closing price $64 7/8 on 1994-02-28"),
    ("XOM", "2005-02-18", 59.41, 0.01, "https://www.nbcnews.com/news/amp/wbna6994181"),
    ("GE", "2005-02-18", 35.88, 0.01, "https://www.nbcnews.com/news/amp/wbna6994181"),
    ("GE", "1998-09-04", 75.50, 0.01, "https://archive.seattletimes.com/archive/?date=19980905&slug=2770248"),
    ("MSFT", "1998-09-04", 96.625, 0.01, "https://archive.seattletimes.com/archive/?date=19980905&slug=2770248"),
    ("AAPL", "2011-08-09", 374.01, 0.01, "https://www.washingtonpost.com/business/economy/apple-overtakes-exxon-mobil-as-most-valuable-company/2011/08/09/gIQACYWq4I_story.html"),
    ("NVDA", "2024-06-18", 135.58, 0.01, "https://www.cnbc.com/2024/06/18/nvidia-passes-microsoft-in-market-cap-is-most-valuable-public-company.html"),
    ("T", "2005-01-28", 23.62, 0.01, "SBC close in AT&T Corp merger proxy (SEC DEFM14A)"),
    ("T", "2014-05-07", 35.76, 0.02, "https://bimajority.org/~wollman/t.html (604 T = $21,599.04)"),
    ("VZ", "2014-05-07", 48.10, 0.02, "https://bimajority.org/~wollman/t.html (166 VZ = $7,984.60)"),
]

# AT&T Corp year-end prices printed in its FY1993 10-K ten-year table (independent of HSI)
T_CORP_10K = {1984: 19.50, 1985: 25.00, 1986: 25.00, 1987: 27.00, 1988: 28.75, 1989: 45.50,
              1990: 30.125, 1991: 39.125, 1992: 51.00, 1993: 52.50}

# (ticker, date, shares of spinco per parent share, spinco symbol) -> compare to Yahoo factor
SPINS = [("IBM", "2021-11-04", 0.2, "KD"), ("GE", "2023-01-04", 1 / 3, "GEHC"), ("GE", "2024-04-02", 0.25, "GEV"),
         ("T", "2022-04-11", 0.241917, "WBD"), ("PFE", "2020-11-17", 0.124079, "VTRS")]


def anchors() -> list[dict]:
    out = []
    for sym, d, ref, tol, src in ANCHORS:
        px = nominal_price(sym)
        got = float(px.loc[:d].iloc[-1])
        dev = got / ref - 1
        out.append({"check": "anchor", "symbol": sym, "date": d, "series": round(got, 4), "reference": ref,
                    "deviation": round(dev, 4), "flag": abs(dev) > tol, "source": src})
    px = nominal_price("T_CORP")
    for y, ref in T_CORP_10K.items():
        got = float(px.loc[:f"{y}-12-31"].iloc[-1])
        dev = got / ref - 1
        out.append({"check": "anchor", "symbol": "T_CORP", "date": f"{y}-12-31", "series": got, "reference": ref,
                    "deviation": round(dev, 4), "flag": abs(dev) > 0.02,
                    "source": "AT&T Corp 10-K FY1993 ten-year table (year-end stock price)"})
    return out


def vendor_crosscheck() -> list[dict]:
    h = pd.read_csv(SOURCES_DIR / "companiesmarketcap_history.csv", parse_dates=["date"])
    out = []
    for t, g in h.groupby("ticker"):
        px = load_yahoo_history(t)["Close"]  # split-adjusted, so real splits do not show up
        s = g.set_index("date")["mcap_usd"]
        s = s[s.index >= px.index[0]]
        q = s.resample("QE").last().dropna()
        p = px.reindex(px.index.union(q.index)).ffill().reindex(q.index)
        implied = (q / p).dropna()
        jump = implied.pct_change().abs()
        bad = jump[jump > 0.10]
        out.append({"check": "cmc_implied_shares", "symbol": t, "date": "",
                    "series": f"{len(implied)} quarters", "reference": "companiesmarketcap",
                    "deviation": round(float(jump.max()), 4) if len(jump.dropna()) else 0.0,
                    "flag": len(bad) > 0,
                    "source": "; ".join(f"{d.date()}:{v:+.0%}" for d, v in bad.items())[:300]})
    return out


def spin_factors() -> list[dict]:
    out = []
    for parent, d, ratio, spin in SPINS:
        h = load_yahoo_history(parent)
        f = float(h.loc[d, "Stock Splits"])
        p_prev = float(nominal_price(parent).loc[:pd.Timestamp(d) - pd.Timedelta(days=1)].iloc[-1])
        p_spin = float(nominal_price(spin).loc[d:].iloc[0])
        documented = ratio * p_spin / p_prev          # spun value as fraction of pre-spin price
        implied = 1 - 1 / f
        out.append({"check": "spinoff_factor", "symbol": parent, "date": d, "series": round(implied, 4),
                    "reference": round(documented, 4), "deviation": round(implied - documented, 4),
                    "flag": abs(implied - documented) > 0.03,
                    "source": f"Yahoo pseudo-split {f} vs {ratio:.4f} {spin} x first {spin} close "
                              f"/ prior {parent} close"})
    return out


def main() -> None:
    rows = anchors() + vendor_crosscheck() + spin_factors()
    df = pd.DataFrame(rows)
    df.to_csv(DATA_QUALITY_DIR / "price_sanity.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 140)
    print(df[df.check != "cmc_implied_shares"].to_string(index=False))
    print("\nFlagged vendor cross-checks:")
    print(df[(df.check == "cmc_implied_shares") & df.flag][["symbol", "deviation", "source"]].to_string(index=False))


if __name__ == "__main__":
    main()

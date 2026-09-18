"""Re-download and normalise every *automatable* Phase 1 source into data/sources/.

Browser-only extractions (Morgan Stanley exhibit decode, EDGAR tables, AT&T
annual reports) are documented in data/sources/README.md; their outputs are
committed as CSVs and are not regenerated here.

Run:  python scripts/fetch_sources.py [wikipedia|sp500|cmc|shiller|att|tbill|all]
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sp500bt.config import SOURCES_DIR  # noqa: E402
from sp500bt.universe import load_universe  # noqa: E402

UA_BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
UA_WIKI = "sp500-backtest-research/1.0 (personal research script)"

WIKI_MCAP_PAGE = "List_of_public_corporations_by_market_capitalization"
WIKI_MCAP_REVID = 1371146339          # pinned revision used for the Phase 1 table
WIKI_SP500_PAGE = "List_of_S%26P_500_companies"
WIKI_SP500_REVID = 1375385207


def _wiki_html(page: str, revid: int) -> str:
    params: dict[str, str | int] = {"action": "parse", "oldid": revid, "prop": "text", "format": "json",
                                    "formatversion": 2}
    r = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers={"User-Agent": UA_WIKI},
                     timeout=60)
    r.raise_for_status()
    return r.json()["parse"]["text"]


def fetch_wikipedia_ft() -> pd.DataFrame:
    """Per-year FT Global 500-based top-10 tables (quarterly from 2006, annual 2000-2005)."""
    soup = BeautifulSoup(_wiki_html(WIKI_MCAP_PAGE, WIKI_MCAP_REVID), "lxml")
    refs: dict[str, str] = {}
    for li in soup.select("ol.references li"):
        a = li.select_one("a.external")
        refs[str(li.get("id", ""))] = str(a["href"]) if a is not None else ""
    rows, year, note = [], None, ""
    for el in soup.find_all(["h3", "p", "table"]):
        if el.name == "h3":
            txt = el.get_text(strip=True)
            year = int(txt) if re.fullmatch(r"(19|20)\d\d", txt) else None
            note = ""
        elif el.name == "p" and year:
            note = el.get_text(" ", strip=True)[:200] or note
        elif el.name == "table" and year:
            trs = el.find_all("tr")
            header = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])]
            quarterly = any("quarter" in h.lower() for h in header)
            hdr_refs = [[refs.get(str(a["href"]).lstrip("#"), "")
                         for s in c.select("sup.reference") if (a := s.find("a")) is not None]
                        for c in trs[0].find_all(["th", "td"])]
            for tr in trs[1:]:
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if not cells or not cells[0].isdigit():
                    continue
                rank = int(cells[0])
                if quarterly:
                    vals = [c for c in cells[1:] if c]
                    for qi, v in enumerate(vals, start=1):
                        m = re.match(r"(.+?)\s+([\d,\.]+)\s*(\[\s*\d+\s*\])?$", re.sub(r"\[\s*\d+\s*\]", "", v).strip())
                        if not m:
                            continue
                        rows.append({"year": year, "period": f"Q{qi}", "rank": rank, "company": m.group(1).strip(),
                                     "value_musd": float(m.group(2).replace(",", "")),
                                     "ref_url": (hdr_refs[min(qi, len(hdr_refs) - 1)] or [""])[0], "table_note": note})
                else:
                    rows.append({"year": year, "period": "annual", "rank": rank, "company": cells[1],
                                 "value_musd": float(cells[-1].replace(",", "")), "ref_url": "", "table_note": note})
    df = pd.DataFrame(rows)
    df["wiki_revision"] = WIKI_MCAP_REVID
    df.to_csv(SOURCES_DIR / "wikipedia_ft_global_top10.csv", index=False)
    return df


def fetch_sp500_constituents() -> pd.DataFrame:
    t = pd.read_html(io.StringIO(_wiki_html(WIKI_SP500_PAGE, WIKI_SP500_REVID)))[0]
    t["wiki_revision"] = WIKI_SP500_REVID
    t.to_csv(SOURCES_DIR / "wikipedia_sp500_constituents.csv", index=False)
    return t


def fetch_cmc(pause: float = 1.0) -> pd.DataFrame:
    """companiesmarketcap.com market-cap histories (embedded chart JSON; units = USD 1e5)."""
    uni = load_universe()
    frames = []
    for r in uni.dropna(subset=["cmc_slug"]).itertuples():
        resp = requests.get(f"https://companiesmarketcap.com/{r.cmc_slug}/marketcap/",
                            headers={"User-Agent": UA_BROWSER}, timeout=60)
        resp.raise_for_status()
        m = re.search(r"data\s*=\s*(\[\{\"d\".*?\}\])", resp.text, re.S)
        if not m:
            raise RuntimeError(f"no chart data for {r.cmc_slug}")
        d = pd.DataFrame(json.loads(m.group(1)))
        d["date"] = pd.to_datetime(d["d"], unit="s").dt.normalize()
        d["ticker"] = r.ticker
        d["mcap_usd"] = d["m"].astype(float) * 1e5
        frames.append(d[["date", "ticker", "mcap_usd"]])
        time.sleep(pause)
    out = pd.concat(frames).drop_duplicates(["ticker", "date"], keep="last").sort_values(["ticker", "date"])
    out.to_csv(SOURCES_DIR / "companiesmarketcap_history.csv", index=False)
    return out


def fetch_shiller() -> None:
    from sp500bt.index_tr import SHILLER_URL, SHILLER_XLS
    r = requests.get(SHILLER_URL, headers={"User-Agent": UA_BROWSER}, timeout=120)
    r.raise_for_status()
    SHILLER_XLS.write_bytes(r.content)


FRED_TB3MS = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TB3MS"


def fetch_tbill() -> pd.DataFrame:
    """3-month Treasury bill secondary-market rate (FRED TB3MS, monthly, % p.a.) -- the
    risk-free rate for Sharpe / Sortino ratios."""
    r = requests.get(FRED_TB3MS, timeout=60)  # FRED stalls on browser-like User-Agents
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "tb3ms_pct"]
    with open(SOURCES_DIR / "fred_tb3ms.csv", "w") as f:
        f.write(f"# FRED TB3MS: 3-Month Treasury Bill Secondary Market Rate, monthly average, percent p.a. "
                f"(Board of Governors of the Federal Reserve System, public domain). Source: {FRED_TB3MS}\n")
        df.to_csv(f, index=False)
    return df


# historicalstockinfo.com AT&T tables ------------------------------------------------------
HSI_PRICES = "https://historicalstockinfo.com/att-corp-stock-prices-table/"
HSI_DIVS = "https://historicalstockinfo.com/att-corp-dividends-reference-sheet/"
_HSI_FIXES = {("1980", "Sep"): ("51.56.3", 51.5625, 'source typo "51.56.3"; read as 51 9/16'),
              ("1981", "Feb"): ("51.56.3", 51.5625, 'source typo "51.56.3"; read as 51 9/16'),
              ("1992", "Feb"): ("374.13", 37.125, 'source typo "374.13"; 37 1/8 consistent with Jan 37.25 / Mar 40.75'),
              ("2005", "Nov"): ("*20.35", 20.35, "source marks this as the 2005-11-18 close (day of SBC merger)")}


def fetch_att_prices() -> pd.DataFrame:
    html = requests.get(HSI_PRICES, headers={"User-Agent": UA_BROWSER}, timeout=60).text
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    t = pd.read_html(io.StringIO(html), converters={m: str for m in months})[0]
    t = t[t["Year"].astype(str).str.fullmatch(r"\d{4}")]
    rows = []
    for _, r in t.iterrows():
        for i, m in enumerate(months):
            raw = str(r[m]).strip()
            if raw in ("nan", "", "None"):
                continue
            note = ""
            if (r["Year"], m) in _HSI_FIXES:
                orig, val, note = _HSI_FIXES[(r["Year"], m)]
                assert raw == orig, (r["Year"], m, raw)
            else:
                val = float(raw)
            d = pd.Timestamp(int(r["Year"]), i + 1, 1) + pd.offsets.MonthEnd(0)
            if (r["Year"], m) == ("2005", "Nov"):
                d = pd.Timestamp("2005-11-18")
            basis = ("pre-divestiture AT&T; high-low average of last trading day" if int(r["Year"]) < 1984
                     else "AT&T Corp month-end close, not split-adjusted")
            rows.append((d.date(), val, raw, basis, note))
    df = pd.DataFrame(rows, columns=["date", "price", "raw", "basis", "fix_note"])
    with open(SOURCES_DIR / "att_monthly_prices_historicalstockinfo.csv", "w") as f:
        f.write(f"# Transcribed from {HSI_PRICES} (site cites NYT archive, S&P Stock Price Record, Yahoo). "
                "Footnotes on source: month-end prices not adjusted for splits; pre-divestiture prices are the "
                "high-low average of the last market day of the month. 1998 missing at source.\n")
        df.to_csv(f, index=False)
    return df


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    jobs = {"wikipedia": fetch_wikipedia_ft, "sp500": fetch_sp500_constituents, "cmc": fetch_cmc,
            "shiller": fetch_shiller, "att": fetch_att_prices, "tbill": fetch_tbill}
    for name, fn in jobs.items():
        if what in (name, "all"):
            print(f"fetching {name} ...")
            out = fn()
            if isinstance(out, pd.DataFrame):
                print(f"  {len(out)} rows")

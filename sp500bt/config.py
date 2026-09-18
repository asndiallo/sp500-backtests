"""Central configuration: paths and the default experiment knobs.

Everything else in the package imports paths from here so the notebook,
the build scripts and the scenario runner all agree on where data lives.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "price_cache"          # yfinance parquet cache (one file per ticker)
MANUAL_PRICES_DIR = DATA_DIR / "manual_prices"  # hand-built series for symbols Yahoo lacks
SOURCES_DIR = DATA_DIR / "sources"            # raw extracts of every Phase 1 source
RESULTS_DIR = ROOT / "results"

TOP_HOLDINGS_CSV = DATA_DIR / "largest_company_by_quarter.csv"
CORP_ACTIONS_CSV = DATA_DIR / "corporate_actions.csv"

START_DATE = "1975-01-01"
AS_OF_DATE = "2026-01-02"      # valuation date for every scenario
CONTRIB_AMOUNT = 500.0         # per leg, per period
CONTRIB_FREQ = "QS"            # quarter-start contributions

# Long-run total-return index for the index leg: daily ^GSPC + Shiller dividends
# before 1988, spliced onto ^SP500TR from its first print (see sp500bt.index_tr).
INDEX_TICKER = "SPX_TR"

for _d in (CACHE_DIR, MANUAL_PRICES_DIR, SOURCES_DIR, RESULTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

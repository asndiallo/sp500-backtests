"""Warm the parquet price cache for every symbol in data/universe.csv (plus the
index series) and write results/data_quality/price_fetch_report.csv listing any failures.

Nothing is dropped silently: a symbol that still fails after retries is listed
in the report and must be fixed (corrected symbol / manual series) or logged as
a known gap in REPORT.md.

Run:  python scripts/cache_prices.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sp500bt.config import DATA_QUALITY_DIR, MANUAL_PRICES_DIR  # noqa: E402
from sp500bt.prices import load_yahoo_history  # noqa: E402
from sp500bt.universe import load_universe  # noqa: E402

EXTRA = ["^GSPC", "^SP500TR"]  # index inputs for sp500bt.index_tr


def main(retries: int = 4, pause: float = 1.5) -> None:
    symbols = [s for s in load_universe().price_symbol if not (MANUAL_PRICES_DIR / f"{s}.csv").exists()] + EXTRA
    report = []
    for s in symbols:
        err = None
        for attempt in range(retries):
            try:
                h = load_yahoo_history(s)
                report.append({"symbol": s, "status": "ok", "first": h.index.min().date(),
                               "last": h.index.max().date(), "rows": len(h), "error": ""})
                err = None
                break
            except Exception as e:  # noqa: BLE001 -- recorded in the report
                err = f"{type(e).__name__}: {e}"[:300]
                time.sleep(pause * 2 ** attempt)
        if err:
            report.append({"symbol": s, "status": "FAILED", "first": "", "last": "", "rows": 0, "error": err})
            print(f"FAILED {s}: {err}")
        time.sleep(pause)
    df = pd.DataFrame(report)
    df.to_csv(DATA_QUALITY_DIR / "price_fetch_report.csv", index=False)
    print(df.status.value_counts().to_dict())


if __name__ == "__main__":
    main()

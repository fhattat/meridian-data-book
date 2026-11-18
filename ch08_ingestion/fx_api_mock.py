"""fx_api_mock.py - a stand-in for the exchange-rate API (OP02, Chapter 8.3).

get_rates("2026-03-02") -> {"date": "2026-03-02", "base": "USD", "rates": {"CAD": 0.7351, ...}}
Weekends and holidays return an empty "rates" object, like the real API: the business rule
"use the last business day's rate" belongs to silver (ASOF JOIN), not to ingestion.

Run on its own:  python ch08_ingestion/fx_api_mock.py 2026-03-02
"""
import csv
import json
import sys
from functools import lru_cache
from pathlib import Path

FX_FILE = Path("data/raw/ops/fx_rates.csv")


@lru_cache(maxsize=1)
def _table() -> dict:
    rates: dict = {}
    with open(FX_FILE, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rates.setdefault(row["date"], {})[row["currency"]] = float(row["rate_to_usd"])
    return rates


def get_rates(day: str) -> dict:
    """Rates that convert one unit of the currency to USD (rate_to_usd)."""
    return {"date": day, "base": "USD", "rates": _table().get(day, {})}


if __name__ == "__main__":
    print(json.dumps(get_rates(sys.argv[1] if len(sys.argv) > 1 else "2026-03-02"), indent=2))

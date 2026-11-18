# ch03_toolkit/load_sample.py
from pathlib import Path
import duckdb

MM = Path("data/raw/meridian")
BZ = Path("data/raw/bazaarly/csv")  # small version: CSV copy of the dump
con = duckdb.connect("data/meridian.duckdb")
con.execute("CREATE SCHEMA IF NOT EXISTS raw")

files = {
    "mm_stores": MM / "mm_stores.csv",
    "mm_products": MM / "mm_products.csv",
    "mm_loyalty_members": MM / "mm_loyalty_members.csv",
    "bz_users": BZ / "bz_users.csv",
    "bz_products": BZ / "bz_products.csv",
    "bz_orders_2025": BZ / "bz_orders_2025.csv",
    "bz_orders_2026": BZ / "bz_orders_2026.csv",
    "bz_order_items": BZ / "bz_order_items.csv",
}

for table, path in files.items():
    # all_varchar: no type guessing on raw data, read everything as text
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.{table} AS
        SELECT *, '{path.name}' AS _source_file, now() AS _ingested_at
        FROM read_csv('{path}', all_varchar = true)
    """)
    n = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
    print(f"{table}: {n} rows")

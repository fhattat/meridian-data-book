"""clean_silver.py — from bronze to silver (Chapter 9)."""
import argparse
import json
import time
from pathlib import Path

STEPS = ["00_helpers.sql", "10_stores_geo.sql", "20_products.sql", "30_customers.sql",
         "40_pos.sql", "50_bz_orders.sql", "60_inventory_campaigns.sql", "70_xref.sql"]
CHECK_TABLES = ["stores", "products", "customers", "pos_receipts", "pos_lines",
                "bz_orders", "inventory_monthly", "campaign_products", "customer_xref", "product_xref"]


def fix_text(value: str | None) -> str | None:
    """Repairs mojibake (CafÃ©) caused by reading UTF-8 text with the wrong encoding."""
    if value is None:
        return None
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value  # already clean: leave as is


def split_statements(sql_text: str) -> list[str]:
    return [s.strip() for s in sql_text.split(";\n") if s.strip()]


def run(env: str = "local", size: str = "small") -> dict:
    """Reads bronze tables, rebuilds the silver tables and returns a summary."""
    if env != "local":
        raise NotImplementedError("On Databricks use sql/silver/databricks/ with the same run().")
    import duckdb
    from duckdb.typing import VARCHAR

    con = duckdb.connect("data/meridian.duckdb")
    con.create_function("fix_text", fix_text, [VARCHAR], VARCHAR)
    con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    for f in Path("data/layers/bronze").glob("*.parquet"):  # expose Chapter 8's Parquet files as tables
        if not f.stem.startswith("_"):
            con.execute(f"CREATE OR REPLACE VIEW bronze.{f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")

    sql_dir = Path(__file__).parent / "sql" / "silver" / "duckdb"
    summary = {"layer": "silver", "env": env, "size": size, "steps": [], "row_counts": {}, "warnings": []}
    for name in STEPS:
        started = time.time()
        for statement in split_statements((sql_dir / name).read_text(encoding="utf-8")):
            con.execute(statement)
        summary["steps"].append({"step": name, "seconds": round(time.time() - started, 2)})

    Path("data/layers/silver").mkdir(parents=True, exist_ok=True)
    for table in CHECK_TABLES:
        count = con.execute(f"SELECT COUNT(*) FROM silver.{table}").fetchone()[0]
        summary["row_counts"][table] = count
        # pandas, Polars and the Chapter 6 benchmark read the Parquet copy
        con.execute(f"COPY silver.{table} TO 'data/layers/silver/{table}.parquet' (FORMAT parquet)")
        if count == 0:
            summary["warnings"].append(f"silver.{table} is empty")

    unmatched = con.execute(
        "SELECT COUNT(*) FROM silver.inventory_monthly WHERE product_id IS NULL").fetchone()[0]
    if unmatched:
        summary["warnings"].append(f"inventory_monthly: {unmatched} rows did not match a product")
    con.close()
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="local", choices=["local", "databricks"])
    parser.add_argument("--size", default="small", choices=["small", "large"])
    args = parser.parse_args()
    print(json.dumps(run(env=args.env, size=args.size), indent=2, ensure_ascii=False))

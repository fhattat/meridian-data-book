"""build_gold.py - a thin runner that builds the gold layer in the right order (Chapter 11.7).

Usage: python ch11_modeling/build_gold.py --env local

Steps
1. Twin survivorship on silver.product_xref (rule, not by hand): among Bazaarly products with the
   same normalized name, the one with the most filled brand/price/UPC fields survives; on a tie the
   smaller code. The others point to the survivor's master_product_id, get is_survivor = false and
   are written to quality.quarantine with the reason.
2. Bazaarly items are linked to products BY NAME with lib.reconcile.safe_left_join: it stops if the
   right side is not unique or if the row count / total changes ("keep the number").
3. The SQL files in sql/gold/ run in file-name order (dimensions, facts, security, serving views).
4. gold.fact_sales_monthly is reconciled with data/raw/control_totals.json.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))                      # repo: make lib/ importable when run as a script
from lib.reconcile import reconcile, safe_left_join  # noqa: E402

DB = "data/meridian.duckdb"
SQL_DIR = Path(__file__).parent / "sql" / "gold"
CONTROL = "data/raw/control_totals.json"


def split_statements(sql_text: str) -> list[str]:
    """Splits a file on ';' at line end; drops pieces that contain only comments."""
    out = []
    for s in sql_text.split(";\n"):
        code = "\n".join(line for line in s.splitlines() if not line.strip().startswith("--")).strip()
        if code:
            out.append(s.strip())
    return out


SURVIVORSHIP_SQL = """
WITH bz AS (
  SELECT product_id, product_name_norm,
         (brand IS NOT NULL)::INT + (list_price_usd IS NOT NULL)::INT + (upc IS NOT NULL)::INT AS filled
  FROM silver.products
  WHERE source_company = 'BZ' AND NOT is_test
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY product_name_norm
                               ORDER BY filled DESC, TRY_CAST(product_id AS INT)) AS rn,
         FIRST_VALUE(product_id) OVER (PARTITION BY product_name_norm
                               ORDER BY filled DESC, TRY_CAST(product_id AS INT)) AS survivor_id
  FROM bz
)
SELECT r.product_id, r.survivor_id, r.product_name_norm, s.master_product_id AS survivor_master
FROM ranked r
JOIN silver.product_xref s ON s.source_company = 'BZ' AND s.product_id = r.survivor_id
WHERE r.rn > 1
"""


def survivorship(con) -> int:
    twins = con.execute(SURVIVORSHIP_SQL).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for product_id, survivor_id, name_norm, master in twins:
        con.execute("""UPDATE silver.product_xref
                       SET master_product_id = ?, is_survivor = FALSE, match_method = 'twin'
                       WHERE source_company = 'BZ' AND product_id = ?""", [master, product_id])
        payload = json.dumps({"product_id": product_id, "survivor_id": survivor_id, "name_norm": name_norm})
        con.execute("DELETE FROM quality.quarantine WHERE table_name = 'silver.products' AND row_payload = ?",
                    [payload])
        con.execute("INSERT INTO quality.quarantine VALUES ('silver.products', 'twin_product_not_survivor', ?, ?)",
                    [payload, now])
    return len(twins)


def link_items_by_name(con) -> dict:
    bz_items = con.execute("""SELECT order_item_id, product_name, amount_usd FROM silver.bz_order_items""").df()
    bz_names = con.execute("""
        SELECT p.product_id, p.product_name
        FROM silver.products p
        JOIN silver.product_xref x ON x.source_company = p.source_company AND x.product_id = p.product_id
        WHERE p.source_company = 'BZ' AND NOT p.is_test AND x.is_survivor""").df()
    bz_items["amount_usd"] = bz_items["amount_usd"].astype(float)
    bz_items["name_norm"] = bz_items["product_name"].str.strip().str.lower()
    bz_names["name_norm"] = bz_names["product_name"].str.strip().str.lower()
    items = safe_left_join(
        left=bz_items,
        right=bz_names[["name_norm", "product_id"]],
        on="name_norm",
        measure="amount_usd",
        step="bz_items x product by name",
    )
    unmatched = int(items["product_id"].isna().sum())
    con.register("item_product_df", items[["order_item_id", "product_id"]])
    con.execute("CREATE OR REPLACE TABLE silver.bz_item_product AS SELECT * FROM item_product_df")
    return {"items": len(items), "unmatched": unmatched}


def run(env: str = "local", size: str = "small") -> dict:
    if env != "local":
        raise NotImplementedError("On Databricks run the same SQL files with sha2(x, 256) (databricks.yml, Chapter 18).")
    import duckdb
    con = duckdb.connect(DB)
    con.execute("SET TimeZone = 'UTC'")
    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    con.execute("CREATE SCHEMA IF NOT EXISTS quality")
    con.execute("""CREATE TABLE IF NOT EXISTS quality.quarantine (
        table_name VARCHAR, reason VARCHAR, row_payload JSON, quarantined_at TIMESTAMP)""")
    summary = {"layer": "gold", "env": env, "size": size, "steps": [], "row_counts": {}}

    summary["twins_marked"] = survivorship(con)
    summary["name_link"] = link_items_by_name(con)
    for f in sorted(SQL_DIR.glob("*.sql")):
        started = time.time()
        for statement in split_statements(f.read_text(encoding="utf-8")):
            con.execute(statement)
        summary["steps"].append({"step": f.name, "seconds": round(time.time() - started, 2)})

    for (table,) in con.execute("""SELECT table_name FROM information_schema.tables
                                   WHERE table_schema = 'gold' AND table_type = 'BASE TABLE'
                                   ORDER BY 1""").fetchall():
        summary["row_counts"][table] = con.execute(f"SELECT COUNT(*) FROM gold.{table}").fetchone()[0]

    monthly = con.execute("SELECT source_company, period, amount_usd FROM gold.fact_sales_monthly").df()
    monthly["amount_usd"] = monthly["amount_usd"].astype(float)
    summary["reconcile"] = reconcile(monthly, CONTROL, step="gold.fact_sales", raise_on_fail=False)
    con.close()
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--env", default="local", choices=["local", "databricks"])
    p.add_argument("--size", default="small", choices=["small", "large"])
    a = p.parse_args()
    result = run(a.env, a.size)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    raise SystemExit(0 if result["reconcile"]["status"] == "pass" else 1)

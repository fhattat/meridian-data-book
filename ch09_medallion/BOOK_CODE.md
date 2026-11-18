# Chapter 9 — Storage and transformation with Medallion

## Code from the book

Every code block of this chapter, in book order, under the book's section headings.
Runnable files are in this folder; for scripts printed as "(shortened)" in the book, the full version is the file here.

### 9.1 File formats: CSV, JSON, Parquet; row-based and column-based thinking

**Code 9.1**

```sql
SELECT source_company, SUM(amount_usd) AS sales_usd
FROM 'data/layers/silver/pos_lines.parquet'
GROUP BY source_company;
```

### 9.2 Object storage, Delta and Iceberg, partitioning

**Code 9.2**

```sql
CREATE TABLE IF NOT EXISTS meridian.silver.pos_lines (
  receipt_no          STRING,
  line_no             INT,
  store_id            STRING,
  product_id          STRING,
  qty                 INT,
  amount_original     DECIMAL(12,2),
  currency            STRING,
  amount_usd          DECIMAL(12,2),
  receipt_ts_utc      TIMESTAMP,
  receipt_local_date  DATE,
  receipt_month       DATE,
  is_return           BOOLEAN,
  is_test             BOOLEAN,
  source_company      STRING
)
USING DELTA
PARTITIONED BY (receipt_month);
```

**Code 9.3**

```sql
DESCRIBE HISTORY meridian.silver.pos_lines;
SELECT COUNT(*) FROM meridian.silver.pos_lines VERSION AS OF 12;
```

### 9.3 Bronze: don't touch, archive, mark

**Code 9.4**

```sql
SELECT _row_hash, COUNT(DISTINCT _source_file) AS files
FROM meridian.bronze.mm_pos_raw
GROUP BY _row_hash
HAVING COUNT(DISTINCT _source_file) > 1;
```

**Code 9.5**

```sql
SELECT _source_file, _batch_id, COUNT(*) AS row_count
FROM meridian.bronze.mm_pos_raw
GROUP BY _source_file, _batch_id
ORDER BY _source_file;
```

### 9.4 Silver cleaning: rules first, code second

#### Code layout

**Code 9.6**

```text
ch09_medallion/
├── clean_silver.py
└── sql/silver/duckdb/
    ├── 00_helpers.sql        # clean_text, to_usd_amount, ref tables
    ├── 10_stores_geo.sql
    ├── 20_products.sql
    ├── 30_customers.sql
    ├── 40_pos.sql
    ├── 50_bz_orders.sql
    ├── 60_inventory_campaigns.sql
    └── 70_xref.sql
```

#### Helpers

**Code 9.7**

```sql
-- 00_helpers.sql
SET TimeZone = 'UTC';  -- Bazaarly times are UTC; pin the session, otherwise the machine's time zone is used

CREATE OR REPLACE MACRO clean_text(x) AS
  CASE WHEN TRIM(x) IN ('', 'NULL', 'N/A') THEN NULL ELSE TRIM(x) END;

CREATE OR REPLACE MACRO to_usd_amount(x) AS
  TRY_CAST(REPLACE(REPLACE(clean_text(x), '$', ''), ',', '') AS DECIMAL(12,2));

CREATE OR REPLACE VIEW ref_test_records  AS SELECT * FROM read_csv('ref/test_records.csv',  all_varchar = true);
CREATE OR REPLACE VIEW ref_state_aliases AS SELECT * FROM read_csv('ref/state_aliases.csv', all_varchar = true);

CREATE OR REPLACE TABLE silver.channel_codes AS
SELECT clean_text(channel_code) AS channel_code, clean_text(channel_name) AS channel_name
FROM read_csv('ref/channel_codes.csv', all_varchar = true);

CREATE OR REPLACE TABLE silver.fx_rates AS
SELECT CAST(clean_text(date) AS DATE)                   AS rate_date,
       UPPER(clean_text(currency))                     AS currency,
       TRY_CAST(clean_text(rate_to_usd) AS DECIMAL(12,6)) AS rate_to_usd
FROM bronze.ref_fx_rates;
```

#### Stores and receipts

**Code 9.8**

```sql
-- 10_stores_geo.sql (shortened)
CREATE OR REPLACE TABLE silver.stores AS
SELECT
  clean_text(STORE_CD)                       AS store_id,
  clean_text(STORE_NAME)                     AS store_name,
  clean_text(CITY)                           AS city,
  UPPER(clean_text(STATE))                   AS state_code,
  CASE clean_text(REGION) WHEN 'Mid-West' THEN 'Midwest' ELSE clean_text(REGION) END AS region,
  CASE clean_text(TIME_ZONE)
    WHEN 'ET' THEN 'America/New_York'  WHEN 'CT' THEN 'America/Chicago'
    WHEN 'MT' THEN 'America/Denver'    WHEN 'PT' THEN 'America/Los_Angeles'
  END                                        AS iana_tz,
  'MM'                                       AS source_company
FROM bronze.mm_stores;
```

**Code 9.9**

```sql
-- 40_pos.sql
-- Chapter 8 left POS rows as rec_type + field_1…field_7; first we give the fields their source names.
CREATE OR REPLACE VIEW bronze.mm_pos_named AS
SELECT rec_type,
       field_1 AS RECEIPT_NO,
       CASE WHEN rec_type = 'H' THEN field_2 END AS STORE_CD,
       CASE WHEN rec_type = 'H' THEN field_3 END AS RECEIPT_TS,
       CASE WHEN rec_type = 'H' THEN field_4 END AS REGISTER_NO,
       CASE WHEN rec_type = 'H' THEN field_5 END AS MEMBER_NO,
       CASE WHEN rec_type = 'H' THEN field_6 END AS TENDER_TYPE,
       CASE WHEN rec_type = 'H' THEN field_7 END AS RECEIPT_TOTAL,
       CASE WHEN rec_type = 'L' THEN field_2 END AS LINE_NO,
       CASE WHEN rec_type = 'L' THEN field_3 END AS PROD_CD,
       CASE WHEN rec_type = 'L' THEN field_4 END AS QTY,
       CASE WHEN rec_type = 'L' THEN field_5 END AS UNIT_PRICE,
       CASE WHEN rec_type = 'L' THEN field_6 END AS DISC_AMT,
       CASE WHEN rec_type = 'L' THEN field_7 END AS LINE_AMT,
       _ingested_at, _source_file, _batch_id, _row_hash
FROM bronze.mm_pos_raw;

CREATE OR REPLACE TABLE silver.pos_receipts AS
WITH h AS (
  SELECT r.*, strptime(clean_text(r.RECEIPT_TS), '%m/%d/%Y %I:%M %p') AS ts_local
  FROM bronze.mm_pos_named r
  WHERE r.rec_type = 'H'
)
SELECT
  clean_text(h.RECEIPT_NO)                          AS receipt_no,
  clean_text(h.STORE_CD)                            AS store_id,
  timezone('UTC', timezone(s.iana_tz, h.ts_local))  AS receipt_ts_utc,
  CAST(h.ts_local AS DATE)                          AS receipt_local_date,
  clean_text(h.MEMBER_NO)                           AS member_no,
  clean_text(h.TENDER_TYPE)                         AS tender_type,
  to_usd_amount(h.RECEIPT_TOTAL)                    AS receipt_total_usd,
  COALESCE(clean_text(h.MEMBER_NO) IN (
    SELECT key_value FROM ref_test_records WHERE entity = 'mm_member'), FALSE) AS is_test,
  'MM'                                              AS source_company,
  h._source_file, h._batch_id
FROM h
LEFT JOIN silver.stores s ON s.store_id = clean_text(h.STORE_CD);

CREATE OR REPLACE TABLE silver.pos_lines AS
SELECT
  clean_text(l.RECEIPT_NO)                    AS receipt_no,
  CAST(clean_text(l.LINE_NO) AS INT)          AS line_no,
  h.store_id,
  clean_text(l.PROD_CD)                       AS product_id,
  CAST(clean_text(l.QTY) AS INT)              AS qty,
  to_usd_amount(l.LINE_AMT)                   AS amount_original,
  'USD'                                       AS currency,
  to_usd_amount(l.LINE_AMT)                   AS amount_usd,
  h.receipt_ts_utc,
  h.receipt_local_date,
  CAST(date_trunc('month', h.receipt_local_date) AS DATE) AS receipt_month,
  CAST(clean_text(l.QTY) AS INT) < 0          AS is_return,
  COALESCE(h.is_test, FALSE)                  AS is_test,
  'MM'                                        AS source_company
FROM bronze.mm_pos_named l
LEFT JOIN silver.pos_receipts h ON h.receipt_no = clean_text(l.RECEIPT_NO)
WHERE l.rec_type = 'L';
```

#### Products, inventory and campaigns

**Code 9.10**

```sql
-- 20_products.sql (Meridian side; Bazaarly is added with the same pattern via UNION ALL BY NAME)
CREATE OR REPLACE TABLE silver.products AS
SELECT
  clean_text(PROD_CD)                          AS product_id,
  LPAD(clean_text(UPC), 12, '0')               AS upc,
  fix_text(clean_text(PROD_NAME))              AS product_name,
  LOWER(fix_text(clean_text(PROD_NAME)))       AS product_name_norm,
  clean_text(BRAND)                            AS brand,
  TRIM(split_part(CATEGORY_PATH, '>', 1))      AS category,
  TRIM(split_part(CATEGORY_PATH, '>', 2))      AS subcategory,
  to_usd_amount(UNIT_PRICE)                    AS list_price_usd,
  COALESCE(clean_text(PROD_CD) IN (
    SELECT key_value FROM ref_test_records WHERE entity = 'mm_product'), FALSE) AS is_test,
  'MM'                                         AS source_company
FROM bronze.mm_products;
```

**Code 9.11**

```sql
-- 60_inventory_campaigns.sql
CREATE OR REPLACE TABLE silver.inventory_monthly AS
WITH long AS (
  UNPIVOT (SELECT * EXCLUDE (_ingested_at, _source_file, _batch_id, _row_hash)
           FROM bronze.mm_inventory_monthly)
  ON COLUMNS(* EXCLUDE (PROD_NAME))
  INTO NAME month_text VALUE units_text
)
SELECT
  clean_text(long.PROD_NAME)                                   AS product_name_raw,
  p.product_id,                                                -- the 3 unmatched names stay NULL
  CAST(strptime(long.month_text || '-01', '%Y-%m-%d') AS DATE) AS inventory_month,
  TRY_CAST(clean_text(long.units_text) AS INT)                 AS units,
  'MM'                                                         AS source_company
FROM long
LEFT JOIN silver.products p
  ON p.source_company = 'MM' AND p.product_name_norm = LOWER(TRIM(long.PROD_NAME));

CREATE OR REPLACE TABLE silver.campaign_products AS
WITH exploded AS (
  SELECT clean_text(CAMPAIGN_NAME) AS campaign_name,
         unnest(regexp_split_to_array(PROD_CODES, '[,;]')) AS code
  FROM bronze.mm_campaign_products
)
SELECT campaign_name, TRIM(code) AS product_id, 'MM' AS source_company
FROM exploded
WHERE TRIM(code) <> '';
```

#### Bazaarly orders and currency

**Code 9.12**

```sql
-- 50_bz_orders.sql
CREATE OR REPLACE TABLE silver.bz_orders AS
WITH all_orders AS (
  SELECT * FROM bronze.bz_orders_2025
  UNION ALL BY NAME SELECT * FROM bronze.bz_orders_2026
  UNION ALL BY NAME SELECT * FROM bronze.bz_orders_2027
),
typed AS (
  SELECT
    clean_text(order_id)                                          AS order_id,
    clean_text(legacy_ref)                                        AS legacy_ref,     -- populated only in 2025
    COALESCE(clean_text(user_id) IN (
      SELECT key_value FROM ref_test_records WHERE entity = 'bz_user'), FALSE)  AS is_test,
    'BZ-U-' || clean_text(user_id)                                AS customer_id,
    timezone('UTC', CAST(clean_text(order_date) AS TIMESTAMPTZ))  AS order_ts_utc,
    CAST(timezone('America/New_York', CAST(clean_text(order_date) AS TIMESTAMPTZ)) AS DATE)
                                                                  AS order_local_date,
    clean_text(channel_code)                                      AS channel_code,
    clean_text(status_code)                                       AS status_code,
    UPPER(clean_text(currency))                                   AS currency,
    TRY_CAST(clean_text(order_total) AS DECIMAL(12,2))            AS order_total_original
  FROM all_orders
)
SELECT
  t.*,
  CASE WHEN t.currency = 'USD' THEN t.order_total_original
       ELSE ROUND(t.order_total_original * fx.rate_to_usd, 2) END AS order_total_usd,
  fx.rate_date                                                    AS fx_rate_date,
  'BZ'                                                            AS source_company
FROM typed t
ASOF LEFT JOIN silver.fx_rates fx
  ON t.currency = fx.currency AND t.order_local_date >= fx.rate_date;
```

#### Customer and product matching

**Code 9.13**

```sql
-- 70_xref.sql
CREATE OR REPLACE TABLE silver.customer_xref AS
SELECT
  email_norm,
  MAX(CASE WHEN customer_type = 'member'  THEN customer_id END) AS mm_member_id,
  MAX(CASE WHEN customer_type = 'account' THEN customer_id END) AS mm_account_id,
  MAX(CASE WHEN customer_type = 'user'    THEN customer_id END) AS bz_user_id,
  COUNT(*)                                                      AS source_count
FROM silver.customers               -- 30_customers.sql: email_norm = LOWER(TRIM(email))
WHERE email_norm IS NOT NULL AND NOT is_test
GROUP BY email_norm
HAVING COUNT(*) > 1;

-- One row per source product; matched MM and BZ products share the same master_product_id.
CREATE OR REPLACE TABLE silver.product_xref AS
WITH pairs AS (
  SELECT m.product_id AS mm_product_id, b.product_id AS bz_product_id, 'upc' AS match_method
  FROM silver.products m
  JOIN silver.products b
    ON m.source_company = 'MM' AND b.source_company = 'BZ' AND m.upc = b.upc
  WHERE m.upc IS NOT NULL
  UNION ALL
  SELECT mm_product_id, bz_product_id, 'manual' AS match_method
  FROM read_csv('ref/product_mapping.csv', all_varchar = true)
)
SELECT
  CASE WHEN p.source_company = 'MM'      THEN 'MM-' || p.product_id
       WHEN x.mm_product_id IS NOT NULL THEN 'MM-' || x.mm_product_id
       ELSE 'BZ-' || p.product_id END            AS master_product_id,
  p.source_company,
  p.product_id,
  CASE WHEN p.source_company = 'MM' THEN 'anchor'
       ELSE COALESCE(x.match_method, 'single') END AS match_method,
  TRUE                                           AS is_survivor  -- twins are not decided here; Chapter 11 updates this
FROM silver.products p
LEFT JOIN pairs x ON p.source_company = 'BZ' AND x.bz_product_id = p.product_id;

-- OP04: RLS mapping table (read by the row filter in Chapter 11)
CREATE OR REPLACE TABLE silver.security_user_region AS
SELECT LOWER(TRIM(email)) AS email, TRIM(region) AS region   -- region: Northeast | Midwest | South | West | ALL
FROM read_csv('data/raw/security_user_region.csv', all_varchar = true);
```

#### clean_silver.py

**Code 9.14**

```python
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
```

### 9.5 Latest record with ROW_NUMBER, history with LEAD/LAG

**Code 9.15**

```sql
WITH bz_users_current AS (
  SELECT *
  FROM bronze.bz_users
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY clean_text(user_id)
    ORDER BY _ingested_at DESC
  ) = 1
)
SELECT COUNT(*) FROM bz_users_current;
```

**Code 9.16**

```sql
WITH snapshots AS (
  SELECT clean_text(PROD_CD)          AS product_id,
         to_usd_amount(UNIT_PRICE)    AS list_price_usd,
         CAST(_ingested_at AS DATE)   AS snapshot_date
  FROM bronze.mm_products
),
changes AS (
  SELECT *,
         LAG(list_price_usd) OVER (PARTITION BY product_id ORDER BY snapshot_date) AS prev_price
  FROM snapshots
)
SELECT
  product_id,
  list_price_usd,
  snapshot_date                                                        AS valid_from,
  LEAD(snapshot_date) OVER (PARTITION BY product_id ORDER BY snapshot_date) AS valid_to
FROM changes
WHERE prev_price IS NULL OR list_price_usd <> prev_price;
```

### 9.7 Hands-on: having AI write the same silver cleaning in four languages

**Code 9.17**

```python
import pandas as pd

import duckdb  # named POS columns come from the view in 40_pos.sql
raw = duckdb.connect("data/meridian.duckdb", read_only=True).sql("SELECT * FROM bronze.mm_pos_named").df()
stores = pd.read_parquet("data/layers/silver/stores.parquet")[["store_id", "iana_tz"]]

h = raw[raw["rec_type"] == "H"].copy()
h["store_id"] = h["STORE_CD"].str.strip()
h["ts_local"] = pd.to_datetime(h["RECEIPT_TS"].str.strip(), format="%m/%d/%Y %I:%M %p", errors="coerce")
h = h.merge(stores, on="store_id", how="left", validate="many_to_one")

def to_utc(ts, tz):
    if pd.isna(ts) or pd.isna(tz):
        return pd.NaT
    return ts.tz_localize(tz, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC").tz_localize(None)

h["receipt_ts_utc"] = [to_utc(ts, tz) for ts, tz in zip(h["ts_local"], h["iana_tz"])]
h["receipt_total_usd"] = pd.to_numeric(
    h["RECEIPT_TOTAL"].str.replace(r"[$,]", "", regex=True).str.strip(), errors="coerce").round(2)
receipts_pd = h.rename(columns={"RECEIPT_NO": "receipt_no"})[["receipt_no", "receipt_ts_utc", "receipt_total_usd"]]
```

**Code 9.18**

```python
import polars as pl

import duckdb  # named POS columns come from the view in 40_pos.sql
raw = duckdb.connect("data/meridian.duckdb", read_only=True).sql("SELECT * FROM bronze.mm_pos_named").pl()
stores = pl.read_parquet("data/layers/silver/stores.parquet").select("store_id", "iana_tz")

h = (
    raw.filter(pl.col("rec_type") == "H")
    .with_columns(
        pl.col("STORE_CD").str.strip_chars().alias("store_id"),
        pl.col("RECEIPT_TS").str.strip_chars()
          .str.strptime(pl.Datetime, "%m/%d/%Y %I:%M %p", strict=False).alias("ts_local"),
        pl.col("RECEIPT_TOTAL").str.replace_all(r"[$,]", "").str.strip_chars()
          .cast(pl.Decimal(12, 2), strict=False).alias("receipt_total_usd"),
    )
    .join(stores, on="store_id", how="left")
)

# Polars converts time zones with a single zone string, not per row; so we process one zone at a time.
parts = [
    h.filter(pl.col("iana_tz") == tz).with_columns(
        pl.col("ts_local").dt.replace_time_zone(tz, ambiguous="null", non_existent="null")
          .dt.convert_time_zone("UTC").dt.replace_time_zone(None).alias("receipt_ts_utc"))
    for tz in h["iana_tz"].drop_nulls().unique()
]
parts.append(h.filter(pl.col("iana_tz").is_null())
               .with_columns(pl.lit(None, dtype=pl.Datetime("us")).alias("receipt_ts_utc")))
receipts_pl = (pl.concat(parts)
               .select(pl.col("RECEIPT_NO").alias("receipt_no"), "receipt_ts_utc", "receipt_total_usd"))
```

**Code 9.19**

```python
from pyspark.sql import functions as F

raw = spark.table("meridian.bronze.mm_pos_named")
stores = spark.table("meridian.silver.stores").select("store_id", "iana_tz")

receipts_spark = (
    raw.filter(F.col("rec_type") == "H")
    .withColumn("store_id", F.trim("STORE_CD"))
    .withColumn("ts_local", F.expr("try_to_timestamp(trim(RECEIPT_TS), 'MM/dd/yyyy hh:mm a')"))
    .join(stores, "store_id", "left")
    .withColumn("receipt_ts_utc", F.to_utc_timestamp("ts_local", F.col("iana_tz")))
    .withColumn("receipt_total_usd",
                F.expr("try_cast(regexp_replace(trim(RECEIPT_TOTAL), '[$,]', '') AS DECIMAL(12,2))"))
    .select(F.col("RECEIPT_NO").alias("receipt_no"), "receipt_ts_utc", "receipt_total_usd")
)
```

#### Verification: four outputs, one fingerprint

**Code 9.20**

```python
"""compare_outputs.py — compares the output of the four engines with the same measures."""
import pandas as pd

def fingerprint(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "distinct_receipts": int(df["receipt_no"].nunique()),
        "total_usd": round(float(df["receipt_total_usd"].astype(float).sum()), 2),
        "null_ts": int(df["receipt_ts_utc"].isna().sum()),
        "min_ts": str(df["receipt_ts_utc"].min()),
        "max_ts": str(df["receipt_ts_utc"].max()),
    }

def compare(outputs: dict[str, pd.DataFrame], reference: str = "duckdb") -> pd.DataFrame:
    prints = {name: fingerprint(df) for name, df in outputs.items()}
    table = pd.DataFrame(prints).T
    table["matches_reference"] = [prints[name] == prints[reference] for name in table.index]
    return table

# outputs = {"duckdb": receipts_duckdb, "pandas": receipts_pd,
#            "polars": receipts_pl.to_pandas(), "pyspark": receipts_spark.toPandas()}
# print(compare(outputs))
```

### 9.8 Script → tool: clean_silver.py → the “clean” tool

**Code 9.21**

```json
{
  "name": "clean",
  "description": "Rebuilds the silver tables from bronze and returns step durations, row counts and warnings. Writes only to the silver schema. If the warnings list is not empty, always report it to the user.",
  "parameters": {
    "type": "object",
    "properties": {
      "env":  {"type": "string", "enum": ["local", "databricks"], "default": "local"},
      "size": {"type": "string", "enum": ["small", "large"], "default": "small"}
    },
    "required": []
  }
}
```

**Code 9.22**

```json
{
  "layer": "silver",
  "env": "local",
  "size": "small",
  "steps": [{"step": "40_pos.sql", "seconds": 0.0}],
  "row_counts": {"pos_lines": 0, "bz_orders": 0},
  "warnings": ["inventory_monthly: 3 rows did not match a product"]
}
```

**Code 9.23**

```python
import re

# Only table writes are checked; views such as bronze.mm_pos_named in 40_pos.sql copy no data.
WRITE_TARGET = re.compile(r"CREATE\s+OR\s+REPLACE\s+TABLE\s+([a-z_]+)\.", re.IGNORECASE)

def assert_silver_only(statement: str) -> None:
    for schema in WRITE_TARGET.findall(statement):
        if schema.lower() != "silver":
            raise PermissionError(f"the clean tool writes only to silver, target: {schema}")

# inside run(), right before con.execute(statement):
# assert_silver_only(statement)
```

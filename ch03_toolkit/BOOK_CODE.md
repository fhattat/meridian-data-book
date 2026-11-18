# Chapter 3 — Toolkit: environment, SQL and Python

## Code from the book

Every code block of this chapter, in book order, under the book's section headings.
Runnable files are in this folder; for scripts printed as "(shortened)" in the book, the full version is the file here.

### 3.1 Main environment Databricks: first setup, notebook, SQL warehouse, Unity Catalog

**Code 3.1**

```sql
-- Databricks: the book's catalog layout
CREATE CATALOG IF NOT EXISTS meridian;
CREATE SCHEMA IF NOT EXISTS meridian.raw;
CREATE VOLUME IF NOT EXISTS meridian.raw.landing;
CREATE SCHEMA IF NOT EXISTS meridian.bronze;
CREATE SCHEMA IF NOT EXISTS meridian.silver;
CREATE SCHEMA IF NOT EXISTS meridian.gold;
```

### 3.2 A free alternative lab: Colab, Google Drive and DuckDB

**Code 3.2**

```python
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
```

### 3.3 Notebook or script? The minimum of Git and the terminal

**Code 3.3**

```bash
git clone <repo-url>          # copy the repo to your computer
git checkout -b ch03-first-queries # open your own branch
git status                       # what changed?
git add ch03_toolkit/load_sample.py
git commit -m "Add script that loads the sample data into DuckDB"
git push -u origin ch03-first-queries
```

### 3.4 The SQL used most in real projects

**Code 3.4**

```sql
-- In DuckDB the tables live in the raw schema (raw.bz_orders_2025),
-- in Databricks they will live in meridian.bronze.
WITH orders AS (                                   -- CTE: name the step
    SELECT
        order_id,
        user_id,
        channel_code,
        currency,
        CAST(order_total AS DECIMAL(12, 2)) AS order_total
    FROM raw.bz_orders_2025
    WHERE user_id <> '900000'                      -- WHERE: drop the test user
)
SELECT
    CASE channel_code                              -- CASE WHEN: turn the code into meaning
        WHEN '10' THEN 'web'
        WHEN '20' THEN 'ios'
        WHEN '30' THEN 'android'
        WHEN '40' THEN 'partner_api'
        ELSE 'UNMAPPED'
    END                        AS channel,
    o.currency,
    COUNT(*)                   AS order_count,
    COUNT(DISTINCT o.user_id)  AS customer_count,
    SUM(o.order_total)         AS total_amount
FROM orders AS o
LEFT JOIN raw.bz_users AS u                        -- JOIN: enrich without losing rows
    ON o.user_id = u.user_id
GROUP BY 1, 2                                      -- GROUP BY: summarize
ORDER BY total_amount DESC;                        -- ORDER BY: sort
```

### 3.5 SQL patterns specific to data engineering

**Code 3.5**

```sql
WITH real_users AS (
    SELECT user_id FROM raw.bz_users WHERE user_id <> '900000'
)
SELECT o.order_id, o.user_id
FROM raw.bz_orders_2025 AS o
LEFT JOIN real_users AS u ON o.user_id = u.user_id
WHERE u.user_id IS NULL;      -- no match = orphan order
```

**Code 3.6**

```sql
SELECT COUNT(*) AS row_count, COUNT(DISTINCT product_code) AS distinct_codes
FROM raw.bz_products;
```

**Code 3.7**

```sql
SELECT order_id, user_id, order_date, channel_code, currency, order_total,
       'bz_orders_2025' AS _source_table
FROM raw.bz_orders_2025
UNION ALL
SELECT order_id, user_id, order_date, channel_code, currency, order_total,
       'bz_orders_2026' AS _source_table
FROM raw.bz_orders_2026;
```

**Code 3.8**

```sql
SELECT *
FROM bronze.bz_orders_2027
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY order_id ORDER BY _ingested_at DESC
) = 1;
```

**Code 3.9**

```sql
SELECT order_id FROM bronze.bz_orders_2026
EXCEPT
SELECT order_id FROM silver.bz_orders;
```

### 3.6 Thinking in tables in Python: schema and DataFrame

**Code 3.10**

```python
# pandas
import pandas as pd
df = pd.read_csv("data/raw/meridian/mm_loyalty_members.csv", dtype=str)
out = (df[df["MEMBER_NO"] != "999"]
       .groupby("STATE").size()
       .sort_values(ascending=False))

# Polars (lazy: runs when you call collect())
import polars as pl
out = (pl.scan_csv("data/raw/meridian/mm_loyalty_members.csv", infer_schema=False)
       .filter(pl.col("MEMBER_NO") != "999")
       .group_by("STATE").len()
       .sort("len", descending=True)
       .collect())

# DuckDB
import duckdb
out = duckdb.sql("""
    SELECT STATE, count(*) AS n
    FROM read_csv('data/raw/meridian/mm_loyalty_members.csv', all_varchar = true)
    WHERE MEMBER_NO <> '999'
    GROUP BY STATE ORDER BY n DESC
""").df()

# PySpark (spark is ready in a Databricks notebook)
from pyspark.sql import functions as F
df = (spark.read.option("header", True)
      .csv("/Volumes/meridian/raw/landing/mm_loyalty_members.csv"))
out = (df.filter(F.col("MEMBER_NO") != "999")
       .groupBy("STATE").count()
       .orderBy(F.desc("count")))
```

### 3.7 Hands-on: load the data set, analyze the legacy SQL with AI

**Code 3.11**

```bash
python data/generate_data.py --size small --seed 2027 --out data/raw
python ch03_toolkit/load_sample.py
```

**Code 3.12**

```python
import re
from pathlib import Path
from collections import Counter

patterns = {
    "SELECT *": r"select\s+\*",
    "INNER JOIN": r"\binner\s+join\b",
    "LEFT JOIN": r"\bleft\s+(outer\s+)?join\b",
    "CTE (WITH)": r"^\s*with\b",
    "CASE WHEN": r"\bcase\s+when\b",
    "ROW_NUMBER": r"\brow_number\s*\(",
    "DISTINCT": r"\bdistinct\b",
}
counts = Counter()
for f in Path("data/raw/ops/sql_legacy").glob("*.sql"):
    text = f.read_text(encoding="utf-8", errors="replace").lower()
    for name, pat in patterns.items():
        counts[name] += len(re.findall(pat, text, flags=re.MULTILINE))
print(counts.most_common())
```

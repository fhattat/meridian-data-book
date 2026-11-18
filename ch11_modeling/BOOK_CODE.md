# Chapter 11 — Data modeling: star schema and beyond

## Code from the book

Every code block of this chapter, in book order, under the book's section headings.
Runnable files are in this folder; for scripts printed as "(shortened)" in the book, the full version is the file here.

### 11.2 Facts and dimensions, cardinality, filter direction; star, snowflake, galaxy

**Code 11.1**

```sql
-- Does dim_product have duplicate keys?
SELECT product_key, COUNT(*) AS n
FROM gold.dim_product
GROUP BY product_key
HAVING COUNT(*) > 1;

-- Does fact_sales have (orphan) keys with no match in the dimension?
SELECT COUNT(*) AS orphan_rows
FROM gold.fact_sales f
LEFT JOIN gold.dim_product p ON f.product_key = p.product_key
WHERE p.product_key IS NULL;
```

### 11.3 Grain: “What does each row represent?”

**Code 11.2**

```sql
SELECT
  COUNT(*)                          AS sales_lines,
  COUNT(DISTINCT order_id)          AS orders,          -- the correct order count
  COUNT(DISTINCT customer_key)      AS active_customers
FROM gold.fact_sales
WHERE source_company = 'BZ';
```

**Code 11.3**

```sql
WITH sales AS (
  SELECT f.store_key, d.year_month, SUM(f.amount_usd) AS sales_usd
  FROM gold.fact_sales f
  JOIN gold.dim_date d ON f.date_key = d.date_key
  WHERE f.source_company = 'MM'
  GROUP BY f.store_key, d.year_month
),
targets AS (
  SELECT t.store_key, d.year_month, SUM(t.target_usd) AS target_usd
  FROM gold.fact_sales_targets t
  JOIN gold.dim_date d ON t.month_key = d.date_key
  GROUP BY t.store_key, d.year_month
)
SELECT s.store_name, COALESCE(sa.year_month, ta.year_month) AS year_month,
       sa.sales_usd, ta.target_usd
FROM sales sa
FULL OUTER JOIN targets ta
  ON sa.store_key = ta.store_key AND sa.year_month = ta.year_month
JOIN gold.dim_store s ON s.store_key = COALESCE(sa.store_key, ta.store_key);
```

### 11.4 Special dimensions and fact types

**Code 11.4**

```sql
CREATE OR REPLACE TABLE gold.dim_order_flags AS
SELECT DISTINCT
  sha2(concat_ws('|', channel, order_status, payment_type), 256) AS order_flags_key,
  channel, order_status, payment_type
FROM (
  -- Bazaarly: channel from the code mapping, payment type from the payment via the invoice
  SELECT COALESCE(c.channel_name, 'UNMAPPED') AS channel,
         COALESCE(o.status_code, 'unknown')  AS order_status,
         COALESCE(p.method, 'unknown')       AS payment_type
  FROM silver.bz_orders o
  LEFT JOIN silver.channel_codes c ON o.channel_code = c.channel_code
  LEFT JOIN silver.invoices i      ON i.order_id = o.order_id
  LEFT JOIN silver.payments p      ON p.invoice_id = i.invoice_id
  UNION
  -- Meridian: store sale, payment type from the receipt
  SELECT 'store', 'completed', COALESCE(r.tender_type, 'unknown')
  FROM silver.pos_receipts r
) flags;
```

**Code 11.5**

```sql
SELECT ship.state_code AS ship_to_state, bill.state_code AS bill_to_state,
       SUM(f.amount_usd) AS sales_usd
FROM gold.fact_sales f
JOIN gold.dim_geo ship ON f.ship_to_geo_key = ship.geo_key
JOIN gold.dim_geo bill ON f.bill_to_geo_key = bill.geo_key
WHERE f.source_company = 'BZ'
GROUP BY ship.state_code, bill.state_code;
```

### 11.5 SCD: keeping the history of changing dimensions

**Code 11.6**

```sql
-- 1) Close the current version of changed customers
MERGE INTO gold.dim_customer AS d
USING silver.customers AS s
  ON d.customer_id = s.customer_id AND d.is_current = true
WHEN MATCHED AND (d.state_code IS DISTINCT FROM s.state_code OR d.region IS DISTINCT FROM s.region) THEN
  UPDATE SET d.valid_to = current_date() - INTERVAL 1 DAY, d.is_current = false;  -- ranges must not overlap

-- 2) Insert a current version for new and changed customers
INSERT INTO gold.dim_customer
SELECT sha2(concat_ws('|', s.customer_id, CAST(current_date() AS STRING)), 256) AS customer_key,
       s.customer_id, s.source_company, s.customer_type, s.state_code, s.region,
       current_date() AS valid_from, DATE '9999-12-31' AS valid_to, true AS is_current
FROM silver.customers s
LEFT JOIN gold.dim_customer d
  ON d.customer_id = s.customer_id AND d.is_current = true
WHERE d.customer_id IS NULL;
```

### 11.6 A model per domain and row-level security

**Code 11.7**

```sql
CREATE OR REPLACE FUNCTION gold.region_filter(row_region STRING)
RETURNS BOOLEAN
RETURN EXISTS (
  SELECT 1 FROM silver.security_user_region s
  WHERE s.email = current_user()
    AND (s.region = row_region OR s.region = 'ALL')
);

-- To apply the filter we expose a view based on the dimension instead of adding a region column to the fact
CREATE OR REPLACE VIEW gold.v_fact_sales_secure AS
SELECT f.*
FROM gold.fact_sales f
JOIN gold.dim_store st ON f.store_key = st.store_key
WHERE gold.region_filter(st.region);
```

### 11.7 From Meridian and Bazaarly data to a clean model

**Code 11.8**

```sql
CREATE OR REPLACE TABLE gold.dim_product AS
WITH members AS (
  SELECT x.master_product_id, x.source_company, x.product_id,
         p.product_name, p.brand, p.category, p.subcategory, p.upc,
         ROW_NUMBER() OVER (
           PARTITION BY x.master_product_id
           ORDER BY CASE x.source_company WHEN 'MM' THEN 0 ELSE 1 END
         ) AS pick
  FROM silver.product_xref x
  JOIN silver.products p
    ON p.source_company = x.source_company AND p.product_id = x.product_id
  WHERE x.is_survivor AND NOT p.is_test
),
codes AS (
  SELECT master_product_id,
         MAX(CASE WHEN source_company = 'MM' THEN product_id END) AS mm_product_code,
         MAX(CASE WHEN source_company = 'BZ' THEN product_id END) AS bz_product_code
  FROM members
  GROUP BY master_product_id
)
SELECT sha2(m.master_product_id, 256) AS product_key,
       m.master_product_id            AS product_id,
       m.product_name, m.brand, m.category, m.subcategory, m.upc,
       c.mm_product_code, c.bz_product_code
FROM members m
JOIN codes c ON c.master_product_id = m.master_product_id
WHERE m.pick = 1;
```

**Code 11.9**

```python
from lib.reconcile import safe_left_join

# bz_items: silver.bz_order_items, bz_names: silver.products (BZ, excluding test rows)
bz_items["name_norm"] = bz_items["product_name"].str.strip().str.lower()
bz_names["name_norm"] = bz_names["product_name"].str.strip().str.lower()

items = safe_left_join(
    left=bz_items,
    right=bz_names[["name_norm", "product_id"]],
    on="name_norm",
    measure="amount_usd",
    step="bz_items x product by name",
)
```

**Code 11.10**

```sql
WITH ship AS (
  SELECT order_id,
         MIN(shipped_ts_utc)   AS first_shipped_ts_utc,   -- first shipment
         MAX(delivered_ts_utc) AS last_delivered_ts_utc,  -- last delivery
         COUNT(*)              AS shipment_count
  FROM silver.shipments
  GROUP BY order_id
)
SELECT o.order_id, o.order_ts_utc, s.first_shipped_ts_utc, s.last_delivered_ts_utc,
       s.shipment_count
FROM silver.bz_orders o
LEFT JOIN ship s ON s.order_id = o.order_id
WHERE NOT o.is_test;
```

**Code 11.11**

```python
from lib.reconcile import reconcile

report = reconcile(
    df=fact_sales_monthly,      # source_company, period (YYYY-MM), amount_usd = SUM(amount_usd)
    control_totals_path="data/raw/control_totals.json",
    step="gold.fact_sales",
    raise_on_fail=False,
)
assert report["status"] == "pass", report["diffs"]
```

### 11.8 Experiment: asking AI the same question on raw and modeled data

**Code 11.12**

```yaml
# ch11_modeling/questions.yaml
- id: q01
  question: "What were the two companies' total net sales in 2026, in USD?"
  traps: [currency, returns, test records]
  tolerance: 0.01          # 1%
- id: q02
  question: "How many orders were placed on Bazaarly in March 2027?"
  traps: [COUNT vs COUNT DISTINCT, tables split by year]
- id: q03
  question: "What were the three best-selling product categories in 2026?"
  traps: [twin products, category path in one column]
- id: q04
  question: "Which Census region beat its target by the largest margin in 2026?"
  traps: [different grain, drill-across]
- id: q05
  question: "On Bazaarly, how many days on average pass between order and delivery?"
  traps: [double shipments, UTC]
- id: q06
  question: "How many customers are both Meridian members and Bazaarly users?"
  traps: [email case, three different names for a customer]
- id: q07
  question: "How much did Meridian stores sell in Black Friday week 2025?"
  traps: [resent file, local time]
- id: q08
  question: "Which channel takes the largest share of Bazaarly revenue?"
  traps: [encoded channel code, unmapped code 50]
- id: q09
  question: "What is the USD value of sales to Canada in 2026?"
  traps: [exchange rate, weekend rates]
- id: q10
  question: "How many products were put in a campaign but never sold?"
  traps: [list in one cell, factless fact, anti-join]
```

**Code 11.13**

```python
# ch11_modeling/text_to_sql_eval.py
"""Asks the model the same ten questions with different contexts and compares the results with the answer key.

Usage: python ch11_modeling/text_to_sql_eval.py --env local --layer gold
          python ch11_modeling/text_to_sql_eval.py --env local --layer bronze
          (Chapter 18: --layer bronze --guide ref/source_guide.yaml)
"""
import argparse, json, yaml, duckdb

def ask_llm(system: str, question: str) -> str:
    """Call your model's API here; return only the SQL text."""
    raise NotImplementedError

def schema_context(con, layer: str, guide: str | None) -> str:
    rows = con.execute(
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = ? ORDER BY table_name, ordinal_position", [layer]
    ).fetchall()
    text = "\n".join(f"{t}.{c} {d}" for t, c, d in rows)
    if layer == "gold":
        text += "\n\n" + open("ch11_modeling/gold_grain.md").read()  # grain and metric definitions
    if guide:
        text += "\n\n" + open(guide).read()                         # e.g. ref/source_guide.yaml
    return text

def is_correct(result, expected, tolerance) -> bool:
    if isinstance(expected, (int, float)):
        return result is not None and abs(float(result) - expected) <= abs(expected) * tolerance
    return result == expected

def run(layer: str = "gold", guide: str | None = None, repeats: int = 3,
        db: str = "data/meridian.duckdb") -> dict:
    con = duckdb.connect(db, read_only=True)
    system = ("You are a data analyst. Return DuckDB SQL only.\n"
              + schema_context(con, layer, guide))
    answers = json.load(open("data/raw/answer_key.json"))   # generated from control_totals.json
    results = []
    for q in yaml.safe_load(open("ch11_modeling/questions.yaml")):
        for i in range(repeats):
            sql = ask_llm(system, q["question"])
            try:
                value = con.execute(sql).fetchone()[0]
                ok = is_correct(value, answers[q["id"]], q.get("tolerance", 0))
                error = None
            except Exception as exc:
                value, ok, error = None, False, str(exc)[:200]
            results.append({"id": q["id"], "try": i + 1, "ok": ok, "error": error, "sql": sql})
    score = sum(r["ok"] for r in results) / len(results)
    return {"layer": layer, "guide": guide, "repeats": repeats,
            "score": round(score, 3), "results": results}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="local", choices=["local", "databricks"])
    ap.add_argument("--layer", default="gold", choices=["bronze", "gold"])
    ap.add_argument("--guide", default=None, help="description file to add to the schema context")
    ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    out = run(layer=a.layer, guide=a.guide, repeats=a.repeats)   # on Databricks, a SQL warehouse connection instead of db
    print(json.dumps({k: v for k, v in out.items() if k != "results"}, ensure_ascii=False))
```

### 11.9 Script → tool: model_checks.py and the modelleme tool

**Code 11.14**

```python
# ch11_modeling/model_checks.py
import re, glob, json, argparse
from lib.io import read_table
from lib.reconcile import reconcile

GRAINS = {  # table: grain columns
    "gold.fact_sales": ["sales_line_id"],
    "gold.fact_order_process": ["order_id"],
    "gold.fact_inventory": ["product_key", "month_key"],
    "gold.fact_sales_targets": ["store_key", "month_key"],
}
DIM_KEYS = {"gold.dim_product": "product_key", "gold.dim_customer": "customer_key",
            "gold.dim_store": "store_key", "gold.dim_geo": "geo_key"}
NAME_RULE = re.compile(r"^(fact|dim)_[a-z0-9_]+$")

def check_grain(env):
    out = []
    for table, cols in GRAINS.items():
        df = read_table(table, env=env, columns=cols)
        dupes = int(df.duplicated(subset=cols).sum())
        out.append({"check": "grain", "table": table, "status": "pass" if dupes == 0 else "fail",
                    "observed": dupes, "expected": 0})
    return out

def check_dim_keys(env):
    out = []
    for table, key in DIM_KEYS.items():
        df = read_table(table, env=env, columns=[key])
        dupes = int(df[key].duplicated().sum())
        out.append({"check": "dim_key_unique", "table": table,
                    "status": "pass" if dupes == 0 else "fail", "observed": dupes, "expected": 0})
    return out

def check_fact_to_fact_joins(sql_dir="ch11_modeling/sql/gold"):
    pattern = re.compile(r"FROM\s+gold\.fact_\w+.*?JOIN\s+gold\.fact_\w+", re.I | re.S)
    hits = [p for p in glob.glob(f"{sql_dir}/*.sql") if pattern.search(open(p).read())]
    return [{"check": "no_fact_to_fact_join", "status": "pass" if not hits else "fail",
             "observed": hits, "expected": []}]

def check_names(env):
    tables = read_table("information_schema.tables", env=env, where="table_schema = 'gold'")
    bad = [t for t in tables["table_name"] if not NAME_RULE.match(t) and not t.startswith("v_")]
    return [{"check": "naming", "status": "pass" if not bad else "warn", "observed": bad}]

def run(env: str = "local", tables: list[str] | None = None) -> dict:
    results = check_grain(env) + check_dim_keys(env) + check_fact_to_fact_joins() + check_names(env)
    results.append(reconcile(df=read_table("gold.fact_sales_monthly", env=env),
                             control_totals_path="data/raw/control_totals.json", step="gold", raise_on_fail=False))
    if tables:
        results = [r for r in results if r.get("table") in tables or "table" not in r]
    failed = [r for r in results if r["status"] == "fail"]
    return {"status": "fail" if failed else "pass", "failed": len(failed), "results": results}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="local", choices=["local", "databricks"])
    print(json.dumps(run(env=ap.parse_args().env), indent=2, ensure_ascii=False))
```

**Code 11.15**

```json
{
  "name": "modelleme",
  "description": "Checks the health of the gold model: grain, key uniqueness, fact-to-fact joins, naming standard and reconciliation with control totals.",
  "parameters": {
    "type": "object",
    "properties": {
      "env":    {"type": "string", "enum": ["local", "databricks"], "default": "local"},
      "tables": {"type": "array", "items": {"type": "string"},
                 "description": "Check only these tables (all if empty)"}
    }
  },
  "returns": "status (pass|fail), failed (count), results (list of checks)",
  "permissions": "Read-only. Never writes to gold or silver, never drops tables."
}
```

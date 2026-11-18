# Bölüm 10 — Veri kalitesi ve güvenilir pipeline

## Code from the book

Every code block of this chapter, in book order, under the book's section headings (Turkish, as printed).
Runnable files are in this folder; for scripts printed as "(shortened)" the full version is the file here.
Bu dosya bölümdeki bütün kod bloklarını kitaptaki sırasıyla ve alt bölüm başlıklarıyla verir.

### 10.1 Kalite boyutları ve kural şablonu: kural, eşik, önem, sahip, aksiyon

> Kuralları kodun içine dağıtmak yerine tek bir dosyada topluyoruz: ch10_quality/rules.yaml. Dosyayı herkes okuyabilir; bir kuralın eşiğini değiştirmek için kodu açmak gerekmez.

**Code 10.1**

```yaml
# ch10_quality/rules.yaml
version: 1
rules:
  - name: products_id_unique
    table: silver.products
    type: unique
    columns: [product_id]
    max_bad_rows: 0
    severity: critical
    owner: data-eng@meridian.example.com
    action: stop_publish

  - name: pos_lines_keys_not_null
    table: silver.pos_lines
    type: not_null
    columns: [receipt_no, product_id]
    max_bad_rows: 0
    severity: critical
    owner: data-eng@meridian.example.com
    action: quarantine

  - name: bz_orders_status_accepted
    table: silver.bz_orders
    type: accepted_values
    column: status_code
    values: [placed, shipped, delivered, cancelled, returned]
    max_bad_rows: 0
    severity: warning
    owner: bazaarly-app@meridian.example.com
    action: report

  - name: bz_items_have_order
    table: silver.bz_order_items
    type: referential
    column: order_id
    ref_table: silver.bz_orders
    ref_column: order_id
    max_bad_rows: 0
    severity: critical
    owner: data-eng@meridian.example.com
    action: quarantine

  - name: bz_channel_code_mapped
    table: silver.bz_orders
    type: referential
    column: channel_code
    ref_table: silver.channel_codes
    ref_column: channel_code
    max_bad_rows: 0
    severity: warning
    owner: bazaarly-app@meridian.example.com
    action: report

  - name: bz_order_total_matches_lines
    table: silver.bz_orders
    type: header_detail
    key: order_id
    header_amount: order_total_original
    detail_table: silver.bz_order_items
    detail_amount: amount_original
    tolerance: 0.01
    max_bad_rows: 0
    severity: warning
    owner: finance@meridian.example.com
    action: report

  - name: pos_negative_qty_only_returns
    table: silver.pos_lines
    type: expression
    bad_rows_where: "qty < 0 AND NOT is_return"
    max_bad_rows: 0
    severity: warning
    owner: store-ops@meridian.example.com
    action: report

  - name: bz_orders_no_future_dates
    table: silver.bz_orders
    type: expression
    bad_rows_where: "order_ts_utc > CAST(now() AS TIMESTAMP)"
    max_bad_rows: 0
    severity: critical
    owner: data-eng@meridian.example.com
    action: quarantine

  - name: pos_receipts_ts_resolved   # ambiguous times at the DST switch stay NULL (Chapter 9)
    table: silver.pos_receipts
    type: not_null
    columns: [receipt_ts_utc]
    max_bad_rows: 0
    severity: warning
    owner: store-ops@meridian.example.com
    action: report

  - name: pos_receipts_fresh
    table: silver.pos_receipts
    type: freshness
    column: receipt_ts_utc
    max_age_hours: 30
    severity: critical
    owner: data-eng@meridian.example.com
    action: stop_publish

  - name: pos_lines_volume_stable
    table: silver.pos_lines
    type: volume
    date_column: receipt_local_date
    max_change_pct: 40
    severity: warning
    owner: data-eng@meridian.example.com
    action: report
```

### 10.2 Kalite SQL’leri: COUNT, mükerrer kontrolü, anti-join, EXCEPT

> 1. Satır sayısı ve günlük hacim. En basit ve en çok işe yarayan kontrol. Eksik gün ve iki kez yüklenen gün burada hemen görünür.

**Code 10.2**

```sql
SELECT receipt_local_date, COUNT(*) AS lines
FROM silver.pos_lines
GROUP BY receipt_local_date
ORDER BY receipt_local_date DESC
LIMIT 14;
```

> 2. Mükerrer anahtar. COUNT(*) ile COUNT(DISTINCT ...) farkı hızlı bir ölçüdür; QUALIFY ise sorunlu satırların kendisini getirir.

**Code 10.3**

```sql
-- Quick measure: a non-zero difference means duplicates
SELECT COUNT(*) - COUNT(DISTINCT product_id) AS duplicate_rows
FROM silver.products;

-- Offending rows
SELECT *
FROM silver.products
QUALIFY COUNT(*) OVER (PARTITION BY product_id) > 1;
```

> Bu sorgu Bazaarly’nin ikiz ürünlerini bulmaz, çünkü onların kodları farklı. İkizler adın normalleştirilmiş halinde aynıdır. Bu yüzden aynı kontrolü bir de ad üzerinden yapıyoruz:

**Code 10.4**

```sql
SELECT lower(trim(product_name)) AS name_key,
       COUNT(*)                   AS n,
       list(product_id)           AS ids
FROM silver.products
WHERE source_company = 'BZ'
GROUP BY name_key
HAVING COUNT(*) > 1;
```

> 3. Anti-join: yetim satırlar ve eşlenmemiş kodlar. Sol tabloda olup sağ tabloda karşılığı olmayan satırları bulur. Referans bütünlüğünün temel aracı.

**Code 10.5**

```sql
-- Orders whose channel code is missing from the mapping table
SELECT o.channel_code, COUNT(*) AS orders, MIN(o.order_local_date) AS first_seen
FROM silver.bz_orders o
LEFT JOIN silver.channel_codes c ON o.channel_code = c.channel_code
WHERE o.channel_code IS NOT NULL
  AND c.channel_code IS NULL
GROUP BY o.channel_code;
```

> 4. Başlık = satır toplamı. Sipariş başlığındaki toplam, satırların toplamına eşit olmalı. Tutmayan siparişler ya kaynakta hesaplama hatasıdır ya da sonradan değişmiş bir sipariştir.

**Code 10.6**

```sql
WITH lines AS (
  SELECT order_id, SUM(amount_original) AS lines_total
  FROM silver.bz_order_items
  GROUP BY order_id
)
SELECT o.order_id, o.order_total_original, l.lines_total,
       o.order_total_original - l.lines_total AS diff
FROM silver.bz_orders o
JOIN lines l ON o.order_id = l.order_id
WHERE abs(o.order_total_original - l.lines_total) > 0.01
ORDER BY abs(diff) DESC;
```

> 5. EXCEPT: katmanlar arası eksik. Bronze’da olan bir sipariş silver’a ulaşmadıysa nerede kayboldu?

**Code 10.7**

```sql
SELECT order_id FROM bronze.bz_orders_2026
EXCEPT
SELECT order_id FROM silver.bz_orders;
```

> “Hangi yıl?” Deniz bu sorguyu rules.yaml’a kural olarak eklemeden önce taslak YAML satırını Bit’e verdi. Bit kuralı yazmadan önce bir soru sordu: “Bronze’da üç sipariş tablosu var: 2025, 2026 ve 2027. Bu sorgu yalnızca birine bakıyor. Bu yılın bir siparişi…

**Code 10.8**

```sql
-- Orders in any yearly bronze table that never reached silver
WITH bronze_orders AS (
  SELECT order_id FROM bronze.bz_orders_2025
  UNION ALL
  SELECT order_id FROM bronze.bz_orders_2026
  UNION ALL
  SELECT order_id FROM bronze.bz_orders_2027
)
SELECT order_id FROM bronze_orders
EXCEPT
SELECT order_id FROM silver.bz_orders;
```

### 10.3 Schema drift ve “kapı” (gate): sorunlu kayıt bronze’da kalsın

> Sözleşme dosyası Bölüm 7’deki profil aracının ürettiği taslaktır; Deniz onu gözden geçirip zorunlu alanları işaretledi:

**Code 10.9**

```yaml
# contracts/bz_orders.yaml (shortened)
table: bz_orders_2027
owner: bazaarly-app@meridian.example.com
columns:
  - {name: order_id,     type: string,  required: true}
  - {name: user_id,      type: string,  required: true}
  - {name: order_date,   type: timestamp, required: true}
  - {name: channel_code, type: string,  required: true}
  - {name: status_code,  type: string,  required: true}
  - {name: currency,     type: string,  required: true}
  - {name: order_total,  type: decimal, required: true}
  - {name: notes,        type: string,  required: false}
```

> Kapının kendisi birkaç satır:

**Code 10.10**

```python
# lib/schema_gate.py
def schema_gate(batch_columns: list[str], contract: dict) -> dict:
    """Compares a batch's columns with the contract: pass | pass_with_warning | hold."""
    expected = {c["name"] for c in contract["columns"]}
    required = {c["name"] for c in contract["columns"] if c.get("required", True)}
    got = set(batch_columns)
    missing = sorted(required - got)
    unexpected = sorted(got - expected)
    if missing:
        decision = "hold"
    elif unexpected:
        decision = "pass_with_warning"
    else:
        decision = "pass"
    return {"decision": decision, "missing": missing, "unexpected": unexpected}
```

### 10.4 Karantina ve mutabakat: “rakamı koru”

> Karantina bir tablodur: quality.quarantine. Her satırın hangi tablodan geldiği, hangi kurala takıldığı, satırın kendisi (JSON olarak) ve ne zaman ayrıldığı yazılıdır. Karantinadaki satır gold’a girmez ama kaybolmaz. Sorun çözülünce (sözleşme güncellenir,…

**Code 10.11**

```sql
CREATE TABLE IF NOT EXISTS quality.quarantine (
  table_name     VARCHAR,
  reason         VARCHAR,   -- name of the rule it failed
  row_payload    JSON,      -- the full row
  quarantined_at TIMESTAMP
);
```

> Kitabın veri setinde bu “gerçek toplam” hazır: generate_data.py, tuzakları eklemeden önce her şirketin aylık net satışını data/raw/control_totals.json dosyasına yazdı. Gerçek bir şirkette bu dosyanın karşılığı finansın kapanış rakamı, kaynak sistemin kendi…

**Code 10.12**

```python
# lib/reconcile.py
"""Keep the number: protects totals across joins and layer transitions."""
import json

import pandas as pd


class ReconcileError(Exception):
    pass


def safe_left_join(left, right, on, measure, step):
    """Runs a LEFT JOIN; stops if the right side is not unique or the total changes."""
    dup = right[right.duplicated(on, keep=False)]
    if not dup.empty:
        raise ReconcileError(f"{step}: duplicate key in the right table ({len(dup)} rows)\n{dup.head(10)}")
    rows_before, sum_before = len(left), round(left[measure].sum(), 2)
    out = left.merge(right, on=on, how="left", indicator=True)
    rows_after, sum_after = len(out), round(out[measure].sum(), 2)
    if rows_after != rows_before or sum_after != sum_before:
        raise ReconcileError(
            f"{step}: number not kept ({rows_before} → {rows_after} rows, "
            f"{sum_before:,.2f} → {sum_after:,.2f})")
    unmatched = int((out["_merge"] == "left_only").sum())
    print(f"{step}: OK, {rows_before} rows, total {sum_before:,.2f}, unmatched {unmatched}")
    return out.drop(columns="_merge")


def reconcile(df, control_totals_path, step, company=None,
              measure="amount_usd", period_col="period", explained=None,
              tolerance=0.01, raise_on_fail=True) -> dict:
    """Compares the table's monthly totals with the control totals.

    df: period ('YYYY-MM') and the amount column; also source_company when company is not given.
    explained: rows missing from the table for a known reason (e.g. quarantine).
    raise_on_fail: True stops on a difference; False only reports it.
    """
    with open(control_totals_path, encoding="utf-8") as f:
        control_all = json.load(f)["net_sales_usd"]          # {company: {period: amount}}
    companies = [company] if company else sorted(control_all)
    diffs, periods = [], 0
    for c in companies:
        part = df if company else df[df["source_company"] == c]
        report = pd.DataFrame({"control": pd.Series(control_all[c], dtype=float)})
        report["in_table"] = part.groupby(period_col)[measure].sum()
        if explained is not None:
            ex = explained if company else explained[explained["source_company"] == c]
            report["explained"] = ex.groupby(period_col)[measure].sum()
        else:
            report["explained"] = 0.0
        report = report.fillna(0.0)
        report["diff"] = (report["control"] - report["in_table"] - report["explained"]).round(2)
        periods += len(report)
        for period, row in report[report["diff"].abs() > tolerance].iterrows():
            diffs.append({"company": c, "period": period, "diff": float(row["diff"])})
    status = "pass" if not diffs else "fail"
    if diffs and raise_on_fail:
        raise ReconcileError(f"{step}: unexplained difference in {len(diffs)} periods\n{diffs[:10]}")
    print(f"{step}: {status}, {periods} periods, unexplained differences {len(diffs)}")
    return {"check": "reconcile", "step": step, "status": status,
            "periods": periods, "diffs": diffs}
```

### 10.6 Script → araç: quality_checks.py → “kalite” aracı

> Script. Aşağıdaki sürüm DuckDB üzerinde çalışır. Databricks’te aynı SQL’ler spark.sql() ile çalışır, tablo adlarının önüne meridian. gelir; deponun Databricks sürümü yalnızca bağlantı satırlarında farklıdır.

**Code 10.13**

```python
# ch10_quality/quality_checks.py
"""Runs the quality rules in rules.yaml and writes the results to the quality schema."""
import argparse
import json
import uuid
from datetime import datetime, timezone

import duckdb
import yaml


def bad_rows_sql(r: dict) -> str:
    """SQL that selects the rows breaking the rule."""
    t, kind = r["table"], r["type"]
    if kind == "unique":
        cols = ", ".join(r["columns"])
        return f"SELECT * FROM {t} QUALIFY COUNT(*) OVER (PARTITION BY {cols}) > 1"
    if kind == "not_null":
        cond = " OR ".join(f"{c} IS NULL" for c in r["columns"])
        return f"SELECT * FROM {t} WHERE {cond}"
    if kind == "accepted_values":
        values = ", ".join(f"'{v}'" for v in r["values"])
        return f"SELECT * FROM {t} WHERE {r['column']} IS NOT NULL AND {r['column']} NOT IN ({values})"
    if kind == "referential":
        c, rc = r["column"], r["ref_column"]
        return (f"SELECT a.* FROM {t} a LEFT JOIN {r['ref_table']} b ON a.{c} = b.{rc} "
                f"WHERE a.{c} IS NOT NULL AND b.{rc} IS NULL")
    if kind == "expression":
        return f"SELECT * FROM {t} WHERE {r['bad_rows_where']}"
    if kind == "header_detail":
        k = r["key"]
        return (f"SELECT h.* FROM {t} h JOIN (SELECT {k}, SUM({r['detail_amount']}) AS detail_sum "
                f"FROM {r['detail_table']} GROUP BY {k}) d ON h.{k} = d.{k} "
                f"WHERE abs(h.{r['header_amount']} - d.detail_sum) > {r.get('tolerance', 0.01)}")
    raise ValueError(f"Unknown rule type: {kind}")


def measure(con, r: dict) -> tuple[float, float]:
    """Returns (observed, allowed)."""
    if r["type"] == "freshness":
        hours = con.execute(
            f"SELECT date_diff('hour', MAX({r['column']}), CAST(now() AS TIMESTAMP)) FROM {r['table']}"
        ).fetchone()[0]
        return float(hours if hours is not None else 10**6), float(r["max_age_hours"])
    if r["type"] == "volume":
        rows = con.execute(
            f"SELECT {r['date_column']}, COUNT(*) FROM {r['table']} GROUP BY 1 ORDER BY 1 DESC LIMIT 2"
        ).fetchall()
        if len(rows) < 2:
            return 0.0, float(r["max_change_pct"])
        (_, last), (_, previous) = rows
        return round(abs(last - previous) / previous * 100, 1), float(r["max_change_pct"])
    n = con.execute(f"SELECT COUNT(*) FROM ({bad_rows_sql(r)})").fetchone()[0]
    return float(n), float(r.get("max_bad_rows", 0))


def run(rules_path: str = "ch10_quality/rules.yaml", db: str = "data/meridian.duckdb",
        only: list[str] | None = None) -> dict:
    """Runs the rules; this is the function the agent calls."""
    con = duckdb.connect(db)
    con.execute("SET TimeZone = 'UTC'")
    con.execute("CREATE SCHEMA IF NOT EXISTS quality")
    con.execute("""CREATE TABLE IF NOT EXISTS quality.check_results (
        run_id VARCHAR, check_name VARCHAR, table_name VARCHAR, status VARCHAR,
        observed DOUBLE, expected DOUBLE, checked_at TIMESTAMP)""")
    con.execute("""CREATE TABLE IF NOT EXISTS quality.quarantine (
        table_name VARCHAR, reason VARCHAR, row_payload JSON, quarantined_at TIMESTAMP)""")

    with open(rules_path, encoding="utf-8") as f:
        rules = yaml.safe_load(f)["rules"]
    run_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    results = []

    for r in rules:
        if only and r["name"] not in only:
            continue
        observed, expected = measure(con, r)
        if observed <= expected:
            status = "pass"
        else:
            status = "fail" if r["severity"] == "critical" else "warn"
        if status != "pass" and r.get("action") == "quarantine":
            con.execute(
                f"INSERT INTO quality.quarantine SELECT ?, ?, to_json(x), ? FROM ({bad_rows_sql(r)}) x",
                [r["table"], r["name"], now])
        con.execute("INSERT INTO quality.check_results VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [run_id, r["name"], r["table"], status, observed, expected, now])
        results.append({"check": r["name"], "table": r["table"], "status": status,
                        "observed": observed, "expected": expected, "owner": r.get("owner")})

    failed = [x for x in results if x["status"] == "fail"]
    warned = [x for x in results if x["status"] == "warn"]
    return {"run_id": run_id, "checked": len(results), "failed": len(failed),
            "warned": len(warned), "publish_allowed": not failed,
            "problems": failed + warned}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--env", default="local", choices=["local", "databricks"])
    p.add_argument("--rules", default="ch10_quality/rules.yaml")
    args = p.parse_args()
    summary = run(args.rules)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    raise SystemExit(0 if summary["publish_allowed"] else 1)
```

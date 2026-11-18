# ch10_quality/quality_checks.py
"""Runs the quality rules in rules.yaml and writes the results to the quality schema."""
import argparse
import json
import uuid
from datetime import datetime, timezone

import os

import duckdb
import yaml

# repo: the synthetic data ends on 2027-06-30. "Now" for freshness and future-date rules is the
# as-of time of the data set, not the clock of your computer (set MERIDIAN_AS_OF to change it).
AS_OF = os.environ.get("MERIDIAN_AS_OF", "2027-07-01 07:00:00")
NOW_SQL = f"TIMESTAMP '{AS_OF}'"


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
        return f"SELECT * FROM {t} WHERE {r['bad_rows_where'].replace('CAST(now() AS TIMESTAMP)', NOW_SQL)}"
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
            f"SELECT date_diff('hour', MAX({r['column']}), {NOW_SQL}) FROM {r['table']}"
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
    p.add_argument("--size", default="small")          # repo: passed by run_pipeline.py
    args = p.parse_args()
    summary = run(args.rules)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    raise SystemExit(0 if summary["publish_allowed"] else 1)

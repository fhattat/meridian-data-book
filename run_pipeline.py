"""run_pipeline.py - runs the Meridian Market platform end to end.

Usage: python run_pipeline.py --env local --size small
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Book order: Chapter 7 -> 11
STEPS = [
    ("profil",    "ch07_profiling/profile_source.py"),
    ("yukleme",   "ch08_ingestion/ingest_to_bronze.py"),
    ("temizlik",  "ch09_medallion/clean_silver.py"),
    ("kalite",    "ch10_quality/quality_checks.py"),   # exit 1 on a critical failure
    ("gold",      "ch11_modeling/build_gold.py"),
    ("modelleme", "ch11_modeling/model_checks.py"),
]

MONTHLY_SQL = """
SELECT f.source_company,
       d.year_month      AS period,
       SUM(f.amount_usd) AS net_sales_usd
FROM gold.fact_sales f
JOIN gold.dim_date d ON d.date_key = f.date_key
GROUP BY 1, 2
"""


def run_step(name: str, script: str, env: str, size: str) -> int:
    cmd = [sys.executable, script, "--env", env, "--size", size]
    print(f"[{name}] {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def reconcile_gold(env: str) -> dict:
    from lib.reconcile import reconcile
    if env == "local":
        import duckdb
        con = duckdb.connect("data/meridian.duckdb", read_only=True)
        df = con.sql(MONTHLY_SQL).df()
    else:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        spark.sql("USE CATALOG meridian")
        df = spark.sql(MONTHLY_SQL).toPandas()
    return reconcile(df, "data/raw/control_totals.json", step="gold.fact_sales",
                     measure="net_sales_usd", raise_on_fail=False)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--env", choices=["local", "databricks"], default="local")
    p.add_argument("--size", default="small")
    args = p.parse_args()

    started = datetime.now(timezone.utc).isoformat()
    for name, script in STEPS:
        code = run_step(name, script, args.env, args.size)
        if code != 0:
            print(f"[{name}] exit code {code}. Pipeline stopped; later steps did not run.")
            sys.exit(code)

    result = reconcile_gold(args.env)
    Path("reports").mkdir(exist_ok=True)
    out = Path(f"reports/run_{started[:10]}.json")
    out.write_text(json.dumps({"started": started, "reconcile": result}, indent=2, default=str))
    print(f"[reconcile] status: {result['status']} | details: {out}")
    sys.exit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()

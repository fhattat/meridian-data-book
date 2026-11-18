# ch11_modeling/model_checks.py
import re, glob, json, argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo: make lib/ importable
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
    ap.add_argument("--size", default="small")          # repo: passed by run_pipeline.py
    out = run(env=ap.parse_args().env)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    raise SystemExit(0 if out["status"] == "pass" else 1)

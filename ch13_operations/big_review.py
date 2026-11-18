# ch13_operations/big_review.py (shortened)
import json, argparse, os
import duckdb

AS_OF = os.environ.get("MERIDIAN_AS_OF", "2027-07-01 07:00:00")   # repo: "now" of the synthetic data set

def run(history_csv="data/raw/ops/query_history.csv", db="data/meridian.duckdb", days=90, top_n=5):
    con = duckdb.connect(db, read_only=True)
    con.execute(f"""
        CREATE TEMP VIEW qh AS
        SELECT *, CAST(started_at AS TIMESTAMP) AS ts
        FROM read_csv('{history_csv}', header = true)
        WHERE CAST(started_at AS TIMESTAMP) >= TIMESTAMP '{AS_OF}' - INTERVAL {days} DAY
    """)
    # tables per query, separated by ';': 'gold.fact_sales;gold.dim_date'
    con.execute("""
        CREATE TEMP VIEW qh_tables AS
        SELECT query_id, cost_usd, trim(unnest(string_split(tables, ';'))) AS table_name FROM qh
    """)
    catalog = con.execute("""
        SELECT table_schema || '.' || table_name AS t FROM information_schema.tables
        WHERE table_schema IN ('bronze', 'silver', 'gold')
    """).fetchall()
    used = {r[0] for r in con.execute("SELECT DISTINCT table_name FROM qh_tables").fetchall()}
    unused = sorted(t for (t,) in catalog if t not in used and not t.startswith("bronze."))

    total = con.execute("SELECT sum(cost_usd) FROM qh").fetchone()[0] or 0
    top = con.execute(f"""
        SELECT query_id, user_name, round(cost_usd, 2) AS cost_usd, duration_ms
        FROM qh ORDER BY cost_usd DESC LIMIT {top_n}
    """).fetchdf()
    slow_repeated = con.execute("""
        SELECT tables, count(*) AS runs, round(median(duration_ms) / 1000, 1) AS median_s
        FROM qh GROUP BY tables HAVING count(*) >= 20 AND median(duration_ms) > 60000
        ORDER BY runs DESC
    """).fetchdf()
    by_table = con.execute("""
        SELECT table_name, round(sum(cost_usd), 2) AS cost_usd, count(DISTINCT query_id) AS queries
        FROM qh_tables GROUP BY table_name ORDER BY cost_usd DESC
    """).fetchdf()
    return {
        "window_days": days,
        "unused_tables": unused,
        "top_queries_cost_share": round(float(top["cost_usd"].sum()) / total, 3) if total else None,
        "top_queries": top.to_dict("records"),
        "slow_repeated": slow_repeated.to_dict("records"),
        "cost_by_table": by_table.head(15).to_dict("records"),
        "note": "Recommendation only. Dropping a table or stopping its refresh is the table owner's decision.",
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--env", default="local")
    print(json.dumps(run(), indent=2, default=str))

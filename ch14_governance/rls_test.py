"""rls_test.py: verifies that the secure view shows each user exactly the expected regions."""
import duckdb

DB = "data/meridian.duckdb"

def run(env="local"):
    con = duckdb.connect(DB, read_only=True)
    users = con.execute("SELECT email, region FROM silver.security_user_region").fetchall()
    # repo: Meridian rows take the store's region, Bazaarly rows the ship-to region (Canada, United
    # Kingdom, Europe included), so "all regions" is read from the unfiltered view, not from dim_store.
    all_regions = {r[0] for r in con.execute("SELECT DISTINCT region FROM gold.v_fact_sales_region").fetchall()}
    failures = []
    for email, region in users:
        con.execute(f"SET VARIABLE app_user = '{email}'")  # synthetic, safe emails
        seen = {r[0] for r in con.execute(
            "SELECT DISTINCT region FROM gold.v_fact_sales_secure").fetchall()}
        expected = all_regions if region == "ALL" else {region}
        if seen != expected:
            failures.append({"user": email, "expected": sorted(expected), "seen": sorted(seen)})
    # repo: the other two rows of Table 11.7
    con.execute("SET VARIABLE app_user = 'nobody@meridian.example.com'")
    unknown_rows = con.execute("SELECT COUNT(*) FROM gold.v_fact_sales_secure").fetchone()[0]
    if unknown_rows:
        failures.append({"user": "not in the mapping table", "expected_rows": 0, "seen_rows": unknown_rows})
    total = con.execute("SELECT SUM(amount_usd) FROM gold.v_fact_sales_region").fetchone()[0]
    parts = con.execute("SELECT SUM(amount_usd) FROM gold.v_fact_sales_region GROUP BY region").fetchall()
    if abs(float(total) - sum(float(p[0]) for p in parts)) > 0.01:
        failures.append({"check": "regions add up to the HQ total", "total": float(total)})
    return {"users_tested": len(users), "failures": failures,
            "status": "pass" if not failures else "fail"}

if __name__ == "__main__":
    print(run())

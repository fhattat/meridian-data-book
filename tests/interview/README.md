# Appendix C — solutions of the SQL exercises

> All data, company names and files here are synthetic and belong to no real person.

## Solve them yourself first

Solve the eight questions of Appendix C **without AI**, at most 15 minutes each. Then compare with the
solutions here. There is no AI in the interview either: what you gain here is not speed but the habit
of seeing the trap.

## Files

| Question | File | Trap |
|---|---|---|
| 1 | `solutions/q01_orders_without_items.sql` | `NOT IN` and NULL; anti-join |
| 2 | `solutions/q02_current_customer.sql` | more than one row per customer in SCD 2 |
| 3 | `solutions/q03_net_sales_by_region_2026.sql` | Bazaarly Online is in no region (NULL) |
| 4 | `solutions/q04_bazaarly_orders_march_2027.sql` | `COUNT(DISTINCT)`, cancelled and test orders |
| 5 | `solutions/q05_header_vs_lines.sql` | order without items, one-cent tolerance |
| 6 | `solutions/q06_customers_in_both.sql` | e-mail normalization, test records |
| 7 | `solutions/q07_top3_categories_per_store.sql` | `RANK` versus `ROW_NUMBER` (ties) |
| 8 | `solutions/q08_bronze_vs_silver_pos.sql` | text keys with spaces; test records are flagged, not deleted |

`fixture.sql` builds a small test data set; every trap has at least one row.
`test_interview_solutions.py` runs every solution on it and compares with the expected answer.

## Run

From the repository root:

```bash
python -m pytest tests/interview -q
```

The tests use DuckDB. Without DuckDB they fall back to Python's built-in `sqlite3`; that is why the
solutions are written in portable SQL that runs the same on DuckDB, Databricks SQL and SQLite. Shorter
forms such as `QUALIFY` are in the comments of the files.

To try them on the real data:

```bash
duckdb data/meridian.duckdb < tests/interview/solutions/q03_net_sales_by_region_2026.sql
```

On Databricks, prefix the table names with the catalog (e.g. `meridian.gold.fact_sales`).

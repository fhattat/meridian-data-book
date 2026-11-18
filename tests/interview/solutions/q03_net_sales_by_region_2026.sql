-- Question 3: what were the net sales of each Census region in 2026?
-- Trap: Bazaarly's single "Bazaarly Online" store belongs to no Census region.
-- Net sales = SUM(gold.fact_sales.amount_usd): test records and cancellations are not in the fact,
-- returns reduce the total as negative lines (canonical definition, Appendix F and metrics/sales.yaml).
-- Defensive LEFT JOIN: rows with a missing store key are not lost.
SELECT
    COALESCE(s.region, 'Online (Bazaarly)') AS region,
    ROUND(SUM(f.amount_usd), 2)             AS net_sales_usd_2026
FROM gold.fact_sales AS f
JOIN gold.dim_date AS d
  ON d.date_key = f.date_key
LEFT JOIN gold.dim_store AS s
  ON s.store_key = f.store_key
WHERE d.year = 2026
GROUP BY COALESCE(s.region, 'Online (Bazaarly)')
ORDER BY net_sales_usd_2026 DESC;
-- Check: the total of this query must equal the 2026 MM + BZ total in control_totals.json.

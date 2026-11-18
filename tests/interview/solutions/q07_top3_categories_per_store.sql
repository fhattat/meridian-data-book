-- Question 7: which three categories sell best in each store?
-- Trap: ranking ties. RANK gives ties the same rank and skips the next one
-- (1, 1, 3); ROW_NUMBER drops one of the ties arbitrarily; DENSE_RANK does not skip (1, 1, 2).
-- This solution uses RANK: all ties stay in the list, so a store can return more than
-- 3 rows. Say in the interview which one you chose.
SELECT store_name, category, net_sales_usd, sales_rank
FROM (
    SELECT
        s.store_name,
        p.category,
        ROUND(SUM(f.amount_usd), 2) AS net_sales_usd,
        RANK() OVER (PARTITION BY s.store_name ORDER BY SUM(f.amount_usd) DESC) AS sales_rank
    FROM gold.fact_sales AS f
    JOIN gold.dim_store   AS s ON s.store_key   = f.store_key
    JOIN gold.dim_product AS p ON p.product_key = f.product_key
    GROUP BY s.store_name, p.category
) ranked
WHERE sales_rank <= 3
ORDER BY store_name, sales_rank, category;
-- Instead of the subquery in DuckDB / Databricks SQL: ... GROUP BY ... QUALIFY sales_rank <= 3

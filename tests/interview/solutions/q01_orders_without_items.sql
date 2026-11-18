-- Question 1: which orders in silver.bz_orders have no items?
-- Trap: an INNER JOIN silently loses these orders.
-- Solution: anti-join (LEFT JOIN + right key IS NULL).
-- Test orders are not removed; is_test is shown so they can be reviewed separately.
SELECT
    o.order_id,
    o.order_local_date,
    o.status_code,
    o.is_test
FROM silver.bz_orders AS o
LEFT JOIN silver.bz_order_items AS i
       ON i.order_id = o.order_id
WHERE i.order_id IS NULL
ORDER BY o.order_id;

-- Shorter (DuckDB / Databricks SQL): the same result with NOT EXISTS
-- SELECT o.order_id FROM silver.bz_orders o
-- WHERE NOT EXISTS (SELECT 1 FROM silver.bz_order_items i WHERE i.order_id = o.order_id);
-- Do not use NOT IN: a single NULL order_id in the subquery makes the result empty.

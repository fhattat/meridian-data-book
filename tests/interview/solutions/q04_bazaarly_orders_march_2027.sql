-- Question 4: how many orders were placed on Bazaarly in March 2027?
-- Trap: the number of items is not the number of orders; test orders are not counted.
-- "Orders placed" includes cancelled ones (placed, then cancelled).
-- If the question means orders that count for net sales, use the second column; say in your answer
-- which one you counted.
-- The month boundary uses order_local_date (America/New_York business day), not the UTC timestamp.
SELECT
    COUNT(DISTINCT o.order_id) AS orders_placed,
    COUNT(DISTINCT CASE WHEN o.status_code <> 'cancelled' THEN o.order_id END) AS orders_not_cancelled
FROM silver.bz_orders AS o
WHERE o.is_test = FALSE
  AND o.order_local_date >= '2027-03-01'
  AND o.order_local_date <  '2027-04-01';
-- Wrong: COUNT(*) on silver.bz_order_items counts every item as an order.

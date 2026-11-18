-- Question 5: list the orders whose header total does not match the sum of their items.
-- Trap: cent rounding; the item total of an order without items is 0, not NULL.
-- Solution: first sum the items per order, then compare with the header.
-- Compare in the same currency (original) so FX does not interfere (Chapter 10 rule).
WITH lines AS (
    SELECT order_id, SUM(amount_original) AS lines_total
    FROM silver.bz_order_items
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.order_total_original                              AS header_total,
    COALESCE(l.lines_total, 0)                          AS lines_total,
    ROUND(o.order_total_original - COALESCE(l.lines_total, 0), 2) AS diff
FROM silver.bz_orders AS o
LEFT JOIN lines AS l
       ON l.order_id = o.order_id
WHERE o.is_test = FALSE
  AND ABS(o.order_total_original - COALESCE(l.lines_total, 0)) > 0.01
ORDER BY ABS(o.order_total_original - COALESCE(l.lines_total, 0)) DESC;
-- Wrong: joining the header to the items and taking SUM(order_total_original); each header is added once per item.

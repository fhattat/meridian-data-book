-- Question 2: return the current record of every customer in gold.dim_customer.
-- Trap: in SCD 2 a customer has more than one row (version).
-- Solution A (preferred): the is_current flag.
SELECT customer_key, customer_id, valid_from, valid_to
FROM gold.dim_customer
WHERE is_current = TRUE
ORDER BY customer_id;

-- Solution B: without trusting the flag, pick the latest valid_from.
-- If the two disagree, the SCD 2 load has a bug; that makes a good quality test too.
-- SELECT customer_key, customer_id, valid_from, valid_to
-- FROM (
--     SELECT d.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY valid_from DESC) AS rn
--     FROM gold.dim_customer d
-- ) x
-- WHERE rn = 1;
-- Instead of the subquery in DuckDB / Databricks SQL: ... QUALIFY ROW_NUMBER() OVER (...) = 1

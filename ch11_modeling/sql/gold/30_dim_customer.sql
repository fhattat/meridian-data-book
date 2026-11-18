-- 30_dim_customer.sql - member, user and account together; SCD type 2 columns (Chapter 11.5).
-- The first load opens one current version per customer with valid_from = 2025-01-01.
-- The Databricks MERGE that closes and opens versions is in ch11_modeling/examples/scd2_merge_databricks.sql.
CREATE OR REPLACE TABLE gold.dim_customer AS
SELECT sha256(customer_id || '|2025-01-01') AS customer_key,
       customer_id, source_company, customer_type, state_code, region,
       DATE '2025-01-01' AS valid_from, DATE '9999-12-31' AS valid_to, TRUE AS is_current
FROM silver.customers
WHERE NOT is_test
UNION ALL
SELECT sha256('UNKNOWN'), 'UNKNOWN', NULL, 'anonymous', NULL, NULL,
       DATE '2025-01-01', DATE '9999-12-31', TRUE;          -- store receipts without a loyalty card

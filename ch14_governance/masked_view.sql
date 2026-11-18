CREATE OR REPLACE VIEW gold.v_customers_masked AS
SELECT customer_id,
       customer_type,
       regexp_replace(email_norm, '^[^@]+', '***') AS email_masked,
       state_code,
       region
FROM silver.customers
WHERE NOT is_test;

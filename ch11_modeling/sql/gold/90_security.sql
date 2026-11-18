-- 90_security.sql - row-level security exercise and masked view (Chapters 11.6 and 14.5).
-- DuckDB has no users: the session variable app_user stands in for current_user() (an exercise,
-- not a security measure). Region: Meridian sales from the store, Bazaarly sales from the
-- ship-to state's region (Canada, United Kingdom and Europe are visible only to HQ).
CREATE OR REPLACE VIEW gold.v_fact_sales_region AS
SELECT f.*, COALESCE(st.region, g.region) AS region
FROM gold.fact_sales f
JOIN gold.dim_store st ON f.store_key = st.store_key
LEFT JOIN gold.dim_geo g ON f.ship_to_geo_key = g.geo_key;

CREATE OR REPLACE VIEW gold.v_fact_sales_secure AS
SELECT f.*
FROM gold.v_fact_sales_region f
WHERE EXISTS (
  SELECT 1 FROM silver.security_user_region s
  WHERE s.email = getvariable('app_user')
    AND (s.region = f.region OR s.region = 'ALL'));

CREATE OR REPLACE VIEW gold.v_customers_masked AS
SELECT customer_id,
       customer_type,
       regexp_replace(email_norm, '^[^@]+', '***') AS email_masked,
       state_code,
       region
FROM silver.customers
WHERE NOT is_test;

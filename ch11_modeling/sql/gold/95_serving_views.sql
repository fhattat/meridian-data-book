-- 95_serving_views.sql - Chapter 12.1: the BI view and its materialized copy
-- Runs the same on Databricks SQL and DuckDB
CREATE OR REPLACE VIEW gold.v_daily_sales AS
SELECT
    d.date,
    s.region,
    p.category,
    f.source_company,                 -- 'MM' store, 'BZ' online
    SUM(f.quantity)        AS units,
    SUM(f.amount_usd)      AS net_sales_usd,
    COUNT(DISTINCT f.order_id) AS orders
FROM gold.fact_sales f
JOIN gold.dim_date    d ON f.date_key    = d.date_key
JOIN gold.dim_product p ON f.product_key = p.product_key
LEFT JOIN gold.dim_store s ON f.store_key = s.store_key   -- defensive LEFT JOIN: rows with a missing key are not lost
GROUP BY d.date, s.region, p.category, f.source_company;

CREATE OR REPLACE TABLE gold.agg_sales_daily AS
SELECT * FROM gold.v_daily_sales;

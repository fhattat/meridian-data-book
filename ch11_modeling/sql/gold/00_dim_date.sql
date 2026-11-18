-- 00_dim_date.sql - generated from the earliest and latest date used by the facts (Chapter 11.7):
-- a date table that is extended by hand is one day forgotten.
CREATE OR REPLACE TABLE gold.dim_date AS
WITH bounds AS (
  SELECT MIN(d) AS first_day, MAX(d) AS last_day FROM (
    SELECT receipt_local_date AS d FROM silver.pos_lines
    UNION ALL SELECT order_local_date FROM silver.bz_orders
    UNION ALL SELECT CAST(delivered_ts_utc AS DATE) FROM silver.shipments
    UNION ALL SELECT CAST(paid_ts_utc AS DATE) FROM silver.payments
    UNION ALL SELECT spend_date FROM silver.campaign_spend
    UNION ALL SELECT target_month FROM silver.sales_targets
  )
)
SELECT
  CAST(strftime(d, '%Y%m%d') AS INTEGER)  AS date_key,
  CAST(d AS DATE)                         AS date,
  year(d)                                 AS year,
  quarter(d)                              AS quarter,
  month(d)                                AS month,
  strftime(d, '%Y-%m')                    AS year_month,
  strftime(d, '%B')                       AS month_name,
  isodow(d)                               AS day_of_week,     -- 1 = Monday
  isodow(d) IN (6, 7)                     AS is_weekend,
  CAST(date_trunc('month', d) AS DATE) = CAST(d AS DATE) AS is_month_start
FROM bounds, range(CAST(date_trunc('month', first_day) AS TIMESTAMP),
                   CAST(last_day AS TIMESTAMP) + INTERVAL 1 DAY, INTERVAL 1 DAY) AS t(d);

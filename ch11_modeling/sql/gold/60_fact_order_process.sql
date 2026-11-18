-- 60_fact_order_process.sql - accumulating snapshot, grain: one row per Bazaarly order (non-test).
-- Shipments are first rolled up to the order (an order can have two packages, trap 27).
CREATE OR REPLACE TABLE gold.fact_order_process AS
WITH ship AS (
  SELECT order_id,
         MIN(shipped_ts_utc)   AS first_shipped_ts_utc,   -- first shipment
         MAX(delivered_ts_utc) AS last_delivered_ts_utc,  -- last delivery
         COUNT(*)              AS shipment_count
  FROM silver.shipments
  GROUP BY order_id
),
inv AS (   -- payment -> invoice -> order, built in this order
  SELECT i.order_id, MIN(i.invoice_ts_utc) AS invoice_ts_utc, MIN(p.paid_ts_utc) AS paid_ts_utc
  FROM silver.invoices i
  LEFT JOIN silver.payments p ON p.invoice_id = i.invoice_id
  GROUP BY i.order_id
)
SELECT o.order_id,
       CAST(strftime(o.order_local_date, '%Y%m%d') AS INTEGER)                  AS order_date_key,
       CAST(strftime(CAST(v.invoice_ts_utc AS DATE), '%Y%m%d') AS INTEGER)      AS invoice_date_key,
       CAST(strftime(CAST(v.paid_ts_utc AS DATE), '%Y%m%d') AS INTEGER)         AS paid_date_key,
       CAST(strftime(CAST(s.first_shipped_ts_utc AS DATE), '%Y%m%d') AS INTEGER) AS first_shipped_date_key,
       CAST(strftime(CAST(s.last_delivered_ts_utc AS DATE), '%Y%m%d') AS INTEGER) AS delivered_date_key,
       sha256(o.customer_id || '|2025-01-01')                                   AS customer_key,
       sha256(concat_ws('|', a.country, a.state_code, a.city_name))             AS ship_to_geo_key,
       o.status_code,
       o.order_ts_utc, s.first_shipped_ts_utc, s.last_delivered_ts_utc,
       COALESCE(s.shipment_count, 0)                                            AS shipment_count,
       ROUND(date_diff('second', o.order_ts_utc, s.last_delivered_ts_utc) / 86400.0, 2) AS days_to_delivery,
       o.order_total_usd
FROM silver.bz_orders o
LEFT JOIN ship s ON s.order_id = o.order_id
LEFT JOIN inv v ON v.order_id = o.order_id
LEFT JOIN silver.addresses a ON a.address_id = o.ship_address_id
WHERE NOT o.is_test;

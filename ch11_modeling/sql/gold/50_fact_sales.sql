-- 50_fact_sales.sql - grain: one row per sales line (Meridian receipt line or Bazaarly order item).
-- Net sales: test records and cancelled/returned orders excluded, returns netted (negative POS
-- lines), shipping and tax excluded, order-day FX. The order header total is NOT used.
CREATE OR REPLACE TABLE gold.fact_sales AS
WITH bz_orders AS (
  SELECT o.*, COALESCE(c.channel_name, 'UNMAPPED') AS channel,   -- code 50 stays visible as UNMAPPED
         COALESCE(p.method, 'unknown') AS payment_type
  FROM silver.bz_orders o
  LEFT JOIN silver.channel_codes c ON c.channel_code = o.channel_code   -- n:1
  LEFT JOIN silver.invoices i ON i.order_id = o.order_id                 -- 1:0..1
  LEFT JOIN silver.payments p ON p.invoice_id = i.invoice_id             -- 1:0..1
),
mm AS (
  SELECT 'MM-' || l.receipt_no || '-' || l.line_no                       AS sales_line_id,
         CAST(strftime(l.receipt_local_date, '%Y%m%d') AS INTEGER)       AS date_key,
         sha256('MM-' || l.product_id)                                  AS product_key,
         sha256(l.store_id)                                             AS store_key,
         CASE WHEN r.member_no IS NULL THEN sha256('UNKNOWN')
              ELSE sha256('MM-M-' || r.member_no || '|2025-01-01') END  AS customer_key,
         CAST(NULL AS VARCHAR)                                          AS seller_key,
         l.receipt_no                                                   AS order_id,
         sha256(concat_ws('|', 'store', 'completed', COALESCE(r.tender_type, 'unknown'))) AS order_flags_key,
         sha256(concat_ws('|', 'US', s.state_code, s.city))             AS ship_to_geo_key,
         sha256(concat_ws('|', 'US', s.state_code, s.city))             AS bill_to_geo_key,
         'MM'                                                           AS source_company,
         l.qty                                                          AS quantity,
         l.amount_usd
  FROM silver.pos_lines l
  JOIN silver.pos_receipts r ON r.receipt_no = l.receipt_no              -- n:1
  JOIN silver.stores s ON s.store_id = l.store_id                        -- n:1
  WHERE NOT l.is_test
),
bz AS (
  SELECT 'BZ-' || i.order_item_id                                       AS sales_line_id,
         CAST(strftime(i.order_local_date, '%Y%m%d') AS INTEGER)        AS date_key,
         sha256(x.master_product_id)                                    AS product_key,
         sha256('BZ-ONLINE')                                            AS store_key,
         sha256(o.customer_id || '|2025-01-01')                         AS customer_key,
         sha256(i.seller_id)                                            AS seller_key,
         i.order_id,
         sha256(concat_ws('|', o.channel, COALESCE(o.status_code, 'unknown'), o.payment_type)) AS order_flags_key,
         sha256(concat_ws('|', sa.country, sa.state_code, sa.city_name)) AS ship_to_geo_key,
         sha256(concat_ws('|', ba.country, ba.state_code, ba.city_name)) AS bill_to_geo_key,
         'BZ'                                                           AS source_company,
         i.qty                                                          AS quantity,
         i.amount_usd
  FROM silver.bz_order_items i
  JOIN bz_orders o ON o.order_id = i.order_id                            -- n:1
  JOIN silver.bz_item_product p ON p.order_item_id = i.order_item_id     -- 1:1 (name link, build_gold.py)
  JOIN silver.product_xref x ON x.source_company = 'BZ' AND x.product_id = p.product_id   -- 1:1
  LEFT JOIN silver.addresses sa ON sa.address_id = o.ship_address_id     -- n:1
  LEFT JOIN silver.addresses ba ON ba.address_id = o.bill_address_id     -- n:1
  WHERE NOT i.is_test AND i.status_code NOT IN ('cancelled', 'returned')
)
SELECT * FROM mm
UNION ALL BY NAME
SELECT * FROM bz;

-- Monthly totals per company for the "keep the number" check (lib/reconcile.py)
CREATE OR REPLACE VIEW gold.fact_sales_monthly AS
SELECT f.source_company, d.year_month AS period, SUM(f.amount_usd) AS amount_usd
FROM gold.fact_sales f
JOIN gold.dim_date d ON d.date_key = f.date_key
GROUP BY 1, 2;

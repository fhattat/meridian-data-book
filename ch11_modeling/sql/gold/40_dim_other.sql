-- 40_dim_other.sql - dim_seller, dim_geo, dim_campaign, dim_order_flags (junk dimension)
CREATE OR REPLACE TABLE gold.dim_seller AS
SELECT sha256(seller_id) AS seller_key, seller_id, seller_name, commission_rate, country
FROM silver.sellers;

CREATE OR REPLACE TABLE gold.dim_geo AS
SELECT DISTINCT sha256(concat_ws('|', country, state_code, city)) AS geo_key,
       city, state_code, country, region
FROM (
  SELECT city_name AS city, state_code, country, region FROM silver.addresses
  UNION
  SELECT s.city, s.state_code, 'US', s.region FROM silver.stores s
);

CREATE OR REPLACE TABLE gold.dim_campaign AS
SELECT sha256(campaign_id) AS campaign_key, campaign_id, campaign_name, channel, start_date, end_date
FROM silver.campaigns;

CREATE OR REPLACE TABLE gold.dim_order_flags AS
SELECT DISTINCT
  sha256(concat_ws('|', channel, order_status, payment_type)) AS order_flags_key,
  channel, order_status, payment_type
FROM (
  -- Bazaarly: channel from the code mapping, payment type from the payment via the invoice
  SELECT COALESCE(c.channel_name, 'UNMAPPED') AS channel,
         COALESCE(o.status_code, 'unknown')  AS order_status,
         COALESCE(p.method, 'unknown')       AS payment_type
  FROM silver.bz_orders o
  LEFT JOIN silver.channel_codes c ON o.channel_code = c.channel_code
  LEFT JOIN silver.invoices i      ON i.order_id = o.order_id
  LEFT JOIN silver.payments p      ON p.invoice_id = i.invoice_id
  UNION
  -- Meridian: store sale, payment type from the receipt
  SELECT 'store', 'completed', COALESCE(r.tender_type, 'unknown')
  FROM silver.pos_receipts r
) flags;

-- 50_bz_orders.sql
-- repo note: the book's version reads status_code only. Since 2027-04-15 the daily files send the
-- column as "status" (INC-20270416-01, Chapter 13); the contract was updated and silver reads both.
CREATE OR REPLACE TABLE silver.bz_orders AS
WITH all_orders AS (
  SELECT * FROM bronze.bz_orders_2025
  UNION ALL BY NAME SELECT * FROM bronze.bz_orders_2026
  UNION ALL BY NAME SELECT * FROM bronze.bz_orders_2027
),
typed AS (
  SELECT
    clean_text(order_id)                                          AS order_id,
    clean_text(legacy_ref)                                        AS legacy_ref,     -- populated only in 2025
    COALESCE(clean_text(user_id) IN (
      SELECT key_value FROM ref_test_records WHERE entity = 'bz_user'), FALSE)  AS is_test,
    'BZ-U-' || clean_text(user_id)                                AS customer_id,
    timezone('UTC', CAST(clean_text(order_date) AS TIMESTAMPTZ))  AS order_ts_utc,
    CAST(timezone('America/New_York', CAST(clean_text(order_date) AS TIMESTAMPTZ)) AS DATE)
                                                                  AS order_local_date,
    clean_text(channel_code)                                      AS channel_code,
    COALESCE(clean_text(status_code), clean_text(status))         AS status_code,    -- Chapter 13 fix
    UPPER(clean_text(currency))                                   AS currency,
    TRY_CAST(clean_text(order_total) AS DECIMAL(12,2))            AS order_total_original,
    clean_text(ship_address_id)                                   AS ship_address_id,
    clean_text(bill_address_id)                                   AS bill_address_id
  FROM all_orders
)
SELECT
  t.*,
  CASE WHEN t.currency = 'USD' THEN t.order_total_original
       ELSE ROUND(t.order_total_original * fx.rate_to_usd, 2) END AS order_total_usd,
  CASE WHEN t.currency = 'USD' THEN 1 ELSE fx.rate_to_usd END    AS fx_rate_to_usd,
  fx.rate_date                                                    AS fx_rate_date,
  'BZ'                                                            AS source_company
FROM typed t
ASOF LEFT JOIN silver.fx_rates fx
  ON t.currency = fx.currency AND t.order_local_date >= fx.rate_date;

-- BZ06: one row per item. The product is linked by NAME (trap 25); the link is made in gold
-- (Chapter 11.7, safe_left_join). Each item is converted with its order's rate and rounded once.
CREATE OR REPLACE TABLE silver.bz_order_items AS
SELECT
  clean_text(i.order_item_id)                       AS order_item_id,
  clean_text(i.order_id)                            AS order_id,
  clean_text(i.product_name)                        AS product_name,
  clean_text(i.seller_id)                           AS seller_id,
  TRY_CAST(clean_text(i.qty) AS INT)                AS qty,
  TRY_CAST(clean_text(i.unit_price) AS DECIMAL(12,2)) AS unit_price_original,
  TRY_CAST(clean_text(i.amount) AS DECIMAL(12,2))   AS amount_original,
  o.currency,
  CASE WHEN o.currency = 'USD' THEN TRY_CAST(clean_text(i.amount) AS DECIMAL(12,2))
       ELSE ROUND(TRY_CAST(clean_text(i.amount) AS DECIMAL(12,2)) * o.fx_rate_to_usd, 2) END AS amount_usd,
  o.order_ts_utc,
  o.order_local_date,
  o.status_code,
  o.is_test,
  'BZ'                                              AS source_company
FROM bronze.bz_order_items i
LEFT JOIN silver.bz_orders o ON o.order_id = clean_text(i.order_id);

-- BZ07: the key chain order -> invoice -> payment, and shipments (an order can have two packages)
CREATE OR REPLACE TABLE silver.invoices AS
SELECT clean_text(invoice_id) AS invoice_id, clean_text(order_id) AS order_id,
       timezone('UTC', CAST(clean_text(invoice_date) AS TIMESTAMPTZ)) AS invoice_ts_utc,
       TRY_CAST(clean_text(amount) AS DECIMAL(12,2)) AS amount_original,
       UPPER(clean_text(currency)) AS currency
FROM bronze.bz_invoices;

CREATE OR REPLACE TABLE silver.payments AS
SELECT clean_text(payment_id) AS payment_id, clean_text(invoice_id) AS invoice_id,
       LOWER(clean_text(method)) AS method,
       TRY_CAST(clean_text(amount) AS DECIMAL(12,2)) AS amount_original,
       timezone('UTC', CAST(clean_text(paid_at) AS TIMESTAMPTZ)) AS paid_ts_utc
FROM bronze.bz_payments;

CREATE OR REPLACE TABLE silver.shipments AS
SELECT clean_text(shipment_id) AS shipment_id, clean_text(order_id) AS order_id,
       clean_text(carrier) AS carrier,
       timezone('UTC', CAST(clean_text(shipped_at) AS TIMESTAMPTZ))   AS shipped_ts_utc,
       timezone('UTC', CAST(clean_text(delivered_at) AS TIMESTAMPTZ)) AS delivered_ts_utc
FROM bronze.bz_shipments;          -- Sheet1.csv, the exact copy, was never loaded (Chapter 7)

-- BZ03: sellers; the commission rate arrives as text ("12%")
CREATE OR REPLACE TABLE silver.sellers AS
SELECT clean_text(seller_id) AS seller_id, clean_text(seller_name) AS seller_name,
       TRY_CAST(REPLACE(clean_text(commission_rate), '%', '') AS DECIMAL(5,2)) / 100 AS commission_rate,
       UPPER(clean_text(country)) AS country,
       TRY_CAST(clean_text(joined_at) AS DATE) AS joined_date
FROM bronze.bz_sellers;

-- BZ10: card transactions for the fraud model (Chapter 12.3)
CREATE OR REPLACE TABLE silver.payment_transactions AS
SELECT clean_text(txn_id) AS txn_id, clean_text(order_id) AS order_id, clean_text(user_id) AS user_id,
       clean_text(device_id) AS device_id, clean_text(card_country) AS card_country,
       clean_text(ip_country) AS ip_country, TRY_CAST(clean_text(hour) AS INT) AS hour,
       TRY_CAST(clean_text(amount_usd) AS DECIMAL(12,2)) AS amount_usd,
       clean_text(is_fraud) IN ('1', 'True', 'true') AS is_fraud
FROM bronze.bz_payment_transactions;

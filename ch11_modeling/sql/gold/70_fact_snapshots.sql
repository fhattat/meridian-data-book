-- 70_fact_snapshots.sql - fact_inventory (periodic snapshot), fact_sales_targets, fact_campaign_spend,
-- fact_promotion_coverage (factless)
CREATE OR REPLACE TABLE gold.fact_inventory AS
SELECT sha256('MM-' || i.product_id)                                  AS product_key,
       CAST(strftime(i.inventory_month, '%Y%m%d') AS INTEGER)        AS month_key,
       i.units
FROM silver.inventory_monthly i
WHERE i.product_id IS NOT NULL;            -- the 3 names without a product stay in silver for the steward

CREATE OR REPLACE TABLE gold.fact_sales_targets AS
SELECT sha256(store_id)                                              AS store_key,
       CAST(strftime(target_month, '%Y%m%d') AS INTEGER)             AS month_key,
       target_usd
FROM silver.sales_targets;

CREATE OR REPLACE TABLE gold.fact_campaign_spend AS
SELECT sha256(campaign_id)                                           AS campaign_key,
       CAST(strftime(spend_date, '%Y%m%d') AS INTEGER)               AS date_key,
       spend_usd, impressions
FROM silver.campaign_spend;

CREATE OR REPLACE TABLE gold.fact_promotion_coverage AS
SELECT DISTINCT c.campaign_key, p.product_key
FROM silver.campaign_products cp
JOIN gold.dim_campaign c ON c.campaign_name = cp.campaign_name
JOIN gold.dim_product p ON p.mm_product_code = cp.product_id;      -- unknown codes (typos) drop out here

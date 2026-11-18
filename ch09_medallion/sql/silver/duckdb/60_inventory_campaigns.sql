-- 60_inventory_campaigns.sql
CREATE OR REPLACE TABLE silver.inventory_monthly AS
WITH long AS (
  UNPIVOT (SELECT * EXCLUDE (_ingested_at, _source_file, _batch_id, _row_hash)
           FROM bronze.mm_inventory_monthly
           WHERE PROD_NAME <> 'PROD_NAME')   -- repo: drop the header row inside the data (trap 3)
  ON COLUMNS(* EXCLUDE (PROD_NAME))
  INTO NAME month_text VALUE units_text
)
SELECT
  clean_text(long.PROD_NAME)                                   AS product_name_raw,
  p.product_id,                                                -- the 3 unmatched names stay NULL
  CAST(strptime(long.month_text || '-01', '%Y-%m-%d') AS DATE) AS inventory_month,
  TRY_CAST(clean_text(long.units_text) AS INT)                 AS units,
  'MM'                                                         AS source_company
FROM long
LEFT JOIN silver.products p
  ON p.source_company = 'MM' AND p.product_name_norm = LOWER(TRIM(long.PROD_NAME));

CREATE OR REPLACE TABLE silver.campaign_products AS
WITH exploded AS (
  SELECT clean_text(CAMPAIGN_NAME) AS campaign_name,
         unnest(regexp_split_to_array(PROD_CODES, '[,;]')) AS code
  FROM bronze.mm_campaign_products
  WHERE clean_text(CAMPAIGN_NAME) <> 'CAMPAIGN_NAME'      -- repo: header row inside the data (trap 3)
)
SELECT campaign_name, TRIM(code) AS product_id, 'MM' AS source_company
FROM exploded
WHERE TRIM(code) <> '';
-- MM07: the campaign log mixes the campaign (dimension) and the daily spend (fact); silver splits them.
CREATE OR REPLACE TABLE silver.campaigns AS
SELECT DISTINCT clean_text(CAMPAIGN_ID) AS campaign_id, clean_text(CAMPAIGN_NAME) AS campaign_name,
       clean_text(CHANNEL) AS channel, CAST(clean_text(START_DATE) AS DATE) AS start_date,
       CAST(clean_text(END_DATE) AS DATE) AS end_date, 'MM' AS source_company
FROM bronze.mm_campaign_log;

CREATE OR REPLACE TABLE silver.campaign_spend AS
SELECT clean_text(CAMPAIGN_ID) AS campaign_id, CAST(clean_text(DAY) AS DATE) AS spend_date,
       TRY_CAST(clean_text(SPEND_USD) AS DECIMAL(12,2)) AS spend_usd,
       TRY_CAST(clean_text(IMPRESSIONS) AS BIGINT) AS impressions
FROM bronze.mm_campaign_log;

-- MM09: targets per store and month; the month arrives as text ('2026-03')
CREATE OR REPLACE TABLE silver.sales_targets AS
SELECT clean_text(STORE_CD) AS store_id,
       CAST(strptime(clean_text(MONTH) || '-01', '%Y-%m-%d') AS DATE) AS target_month,
       TRY_CAST(clean_text(TARGET_USD) AS DECIMAL(14,2)) AS target_usd
FROM bronze.mm_sales_targets;

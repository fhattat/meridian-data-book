-- 70_xref.sql
CREATE OR REPLACE TABLE silver.customer_xref AS
SELECT
  email_norm,
  MAX(CASE WHEN customer_type = 'member'  THEN customer_id END) AS mm_member_id,
  MAX(CASE WHEN customer_type = 'account' THEN customer_id END) AS mm_account_id,
  MAX(CASE WHEN customer_type = 'user'    THEN customer_id END) AS bz_user_id,
  COUNT(*)                                                      AS source_count
FROM silver.customers               -- 30_customers.sql: email_norm = LOWER(TRIM(email))
WHERE email_norm IS NOT NULL AND NOT is_test
GROUP BY email_norm
HAVING COUNT(*) > 1;

-- One row per source product; matched MM and BZ products share the same master_product_id.
CREATE OR REPLACE TABLE silver.product_xref AS
WITH pairs AS (
  SELECT m.product_id AS mm_product_id, b.product_id AS bz_product_id, 'upc' AS match_method
  FROM silver.products m
  JOIN silver.products b
    ON m.source_company = 'MM' AND b.source_company = 'BZ' AND m.upc = b.upc
  WHERE m.upc IS NOT NULL
  UNION ALL
  SELECT mm_product_id, bz_product_id, 'manual' AS match_method
  FROM read_csv('ref/product_mapping.csv', all_varchar = true)
)
SELECT
  CASE WHEN p.source_company = 'MM'      THEN 'MM-' || p.product_id
       WHEN x.mm_product_id IS NOT NULL THEN 'MM-' || x.mm_product_id
       ELSE 'BZ-' || p.product_id END            AS master_product_id,
  p.source_company,
  p.product_id,
  CASE WHEN p.source_company = 'MM' THEN 'anchor'
       ELSE COALESCE(x.match_method, 'single') END AS match_method,
  TRUE                                           AS is_survivor  -- twins are not decided here; Chapter 11 updates this
FROM silver.products p
LEFT JOIN pairs x ON p.source_company = 'BZ' AND x.bz_product_id = p.product_id;

-- OP04: RLS mapping table (read by the row filter in Chapter 11)
CREATE OR REPLACE TABLE silver.security_user_region AS
SELECT LOWER(TRIM(email)) AS email, TRIM(region) AS region   -- region: Northeast | Midwest | South | West | ALL
FROM read_csv('data/raw/security_user_region.csv', all_varchar = true);
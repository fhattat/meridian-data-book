-- 20_dim_product.sql (Chapter 11.7). DuckDB writes sha256(x) where Databricks writes sha2(x, 256).
-- build_gold.py runs the twin survivorship on silver.product_xref before this file.
CREATE OR REPLACE TABLE gold.dim_product AS
WITH members AS (
  SELECT x.master_product_id, x.source_company, x.product_id,
         p.product_name, p.brand, p.category, p.subcategory, p.upc,
         ROW_NUMBER() OVER (
           PARTITION BY x.master_product_id
           ORDER BY CASE x.source_company WHEN 'MM' THEN 0 ELSE 1 END
         ) AS pick
  FROM silver.product_xref x
  JOIN silver.products p
    ON p.source_company = x.source_company AND p.product_id = x.product_id
  WHERE x.is_survivor AND NOT p.is_test
),
codes AS (
  SELECT master_product_id,
         MAX(CASE WHEN source_company = 'MM' THEN product_id END) AS mm_product_code,
         MAX(CASE WHEN source_company = 'BZ' THEN product_id END) AS bz_product_code
  FROM members
  GROUP BY master_product_id
)
SELECT sha256(m.master_product_id) AS product_key,
       m.master_product_id            AS product_id,
       m.product_name, m.brand, m.category, m.subcategory, m.upc,
       c.mm_product_code, c.bz_product_code
FROM members m
JOIN codes c ON c.master_product_id = m.master_product_id
WHERE m.pick = 1;
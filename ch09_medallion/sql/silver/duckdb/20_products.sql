-- 20_products.sql (Meridian side; Bazaarly is added with the same pattern via UNION ALL BY NAME)
CREATE OR REPLACE TABLE silver.products AS
SELECT
  clean_text(PROD_CD)                          AS product_id,
  LPAD(clean_text(UPC), 12, '0')               AS upc,
  fix_text(clean_text(PROD_NAME))              AS product_name,
  LOWER(fix_text(clean_text(PROD_NAME)))       AS product_name_norm,
  clean_text(BRAND)                            AS brand,
  TRIM(split_part(CATEGORY_PATH, '>', 1))      AS category,
  TRIM(split_part(CATEGORY_PATH, '>', 2))      AS subcategory,
  to_usd_amount(UNIT_PRICE)                    AS list_price_usd,
  COALESCE(clean_text(PROD_CD) IN (
    SELECT key_value FROM ref_test_records WHERE entity = 'mm_product'), FALSE) AS is_test,
  'MM'                                         AS source_company
FROM bronze.mm_products
UNION ALL BY NAME
SELECT
  clean_text(product_code)                     AS product_id,
  LPAD(clean_text(upc), 12, '0')               AS upc,           -- 'N/A' and '' become NULL
  fix_text(clean_text(product_name))           AS product_name,
  LOWER(fix_text(clean_text(product_name)))    AS product_name_norm,
  clean_text(brand)                            AS brand,
  clean_text(category)                         AS category,
  clean_text(subcategory)                      AS subcategory,
  to_usd_amount(price)                         AS list_price_usd,
  COALESCE(clean_text(product_code) IN (
    SELECT key_value FROM ref_test_records WHERE entity = 'bz_product'), FALSE) AS is_test,
  'BZ'                                         AS source_company
FROM bronze.bz_products;
-- hash_key, source_id and legacy_flag are left in bronze on purpose (Chapter 7: no business meaning).

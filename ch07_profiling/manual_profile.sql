-- DuckDB: without loading the file, every column as text
CREATE OR REPLACE VIEW p AS
SELECT * FROM read_csv('data/raw/bazaarly/csv/bz_products.csv', all_varchar = true);

-- 1. Size and uniqueness
SELECT COUNT(*)                         AS rows,
       COUNT(DISTINCT product_code)     AS distinct_codes,
       COUNT(DISTINCT lower(trim(product_name))) AS distinct_names
FROM p;

-- 2. Completeness: the different spellings of "empty"
SELECT SUM(CASE WHEN upc IS NULL OR trim(upc) IN ('', 'NULL', 'N/A', '-') THEN 1 ELSE 0 END) AS upc_missing,
       SUM(CASE WHEN brand IS NULL OR trim(brand) = '' THEN 1 ELSE 0 END) AS brand_missing
FROM p;

-- 3. Twin-name suspects: same name, different code
SELECT lower(trim(product_name)) AS name_key, COUNT(*) AS n, list(product_code) AS codes
FROM p
GROUP BY 1
HAVING COUNT(*) > 1;

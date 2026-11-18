-- ch11_modeling/reference_answers.sql
-- Reference SQL for the ten questions in questions.yaml, on the gold layer.
-- tests/test_reference_answers.py checks that each query returns the value in data/raw/answer_key.json.
-- Each query is separated by a line "-- @q0N".

-- @q01 What were the two companies' total net sales in 2026, in USD?
SELECT ROUND(SUM(f.amount_usd), 2)
FROM gold.fact_sales f JOIN gold.dim_date d ON d.date_key = f.date_key
WHERE d.year = 2026;

-- @q02 How many orders were placed on Bazaarly in March 2027?
SELECT COUNT(DISTINCT f.order_id)
FROM gold.fact_sales f JOIN gold.dim_date d ON d.date_key = f.date_key
WHERE f.source_company = 'BZ' AND d.year_month = '2027-03';

-- @q03 What were the three best-selling product categories in 2026?
SELECT string_agg(category, ', ' ORDER BY sales DESC) FROM (
  SELECT p.category, SUM(f.amount_usd) AS sales
  FROM gold.fact_sales f
  JOIN gold.dim_date d ON d.date_key = f.date_key
  JOIN gold.dim_product p ON p.product_key = f.product_key
  WHERE d.year = 2026
  GROUP BY p.category ORDER BY sales DESC LIMIT 3);

-- @q04 Which Census region beat its target by the largest margin in 2026? (drill-across)
WITH sales AS (
  SELECT s.region, SUM(f.amount_usd) AS sales_usd
  FROM gold.fact_sales f
  JOIN gold.dim_date d ON d.date_key = f.date_key
  JOIN gold.dim_store s ON s.store_key = f.store_key
  WHERE f.source_company = 'MM' AND d.year = 2026 GROUP BY 1),
targets AS (
  SELECT s.region, SUM(t.target_usd) AS target_usd
  FROM gold.fact_sales_targets t
  JOIN gold.dim_date d ON d.date_key = t.month_key
  JOIN gold.dim_store s ON s.store_key = t.store_key
  WHERE d.year = 2026 GROUP BY 1)
SELECT sales.region FROM sales JOIN targets USING (region)
ORDER BY sales_usd - target_usd DESC LIMIT 1;

-- @q05 On Bazaarly, how many days on average pass between order and delivery?
SELECT ROUND(AVG(date_diff('second', order_ts_utc, last_delivered_ts_utc)) / 86400.0, 2)
FROM gold.fact_order_process
WHERE last_delivered_ts_utc IS NOT NULL AND status_code <> 'cancelled';

-- @q06 How many customers are both Meridian members and Bazaarly users?
SELECT COUNT(*) FROM silver.customer_xref
WHERE mm_member_id IS NOT NULL AND bz_user_id IS NOT NULL;

-- @q07 How much did Meridian stores sell in Black Friday week 2025?
SELECT ROUND(SUM(f.amount_usd), 2)
FROM gold.fact_sales f JOIN gold.dim_date d ON d.date_key = f.date_key
WHERE f.source_company = 'MM' AND d.date BETWEEN DATE '2025-11-24' AND DATE '2025-11-30';

-- @q08 Which channel takes the largest share of Bazaarly revenue?
SELECT o.channel
FROM gold.fact_sales f JOIN gold.dim_order_flags o ON o.order_flags_key = f.order_flags_key
WHERE f.source_company = 'BZ'
GROUP BY o.channel ORDER BY SUM(f.amount_usd) DESC LIMIT 1;

-- @q09 What is the USD value of sales to Canada in 2026?
SELECT ROUND(SUM(f.amount_usd), 2)
FROM gold.fact_sales f
JOIN gold.dim_date d ON d.date_key = f.date_key
JOIN gold.dim_geo g ON g.geo_key = f.ship_to_geo_key
WHERE f.source_company = 'BZ' AND g.country = 'CA' AND d.year = 2026;

-- @q10 How many products were put in a campaign but never sold?
SELECT COUNT(DISTINCT c.product_key)
FROM gold.fact_promotion_coverage c
WHERE NOT EXISTS (SELECT 1 FROM gold.fact_sales f WHERE f.product_key = c.product_key);

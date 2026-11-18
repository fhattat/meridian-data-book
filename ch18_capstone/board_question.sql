-- The board's question: how much did the two companies sell together in 2026? (USD, net, pro forma)
SELECT COALESCE(f.source_company, 'TOTAL') AS company,
       SUM(f.amount_usd)                    AS net_sales_usd_2026
FROM gold.fact_sales f
JOIN gold.dim_date d ON d.date_key = f.date_key
WHERE d.year = 2026
GROUP BY ROLLUP (f.source_company)
ORDER BY company;

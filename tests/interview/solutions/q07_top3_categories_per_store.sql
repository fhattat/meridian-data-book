-- Soru 7: Her mağaza için en çok satan üç kategori hangileri?
-- Tuzak: Eşit satışlarda sıralama. RANK eşitlere aynı sırayı verir ve bir sonraki sırayı atlar
-- (1, 1, 3); ROW_NUMBER eşitlerden birini keyfî olarak eler; DENSE_RANK atlamaz (1, 1, 2).
-- Bu çözüm RANK kullanır: eşit olanların hepsi listede kalır, bu yüzden bir mağazada 3'ten
-- fazla satır çıkabilir. Hangisini seçtiğinizi mülakatta söyleyin.
SELECT store_name, category, net_sales_usd, sales_rank
FROM (
    SELECT
        s.store_name,
        p.category,
        ROUND(SUM(f.amount_usd), 2) AS net_sales_usd,
        RANK() OVER (PARTITION BY s.store_name ORDER BY SUM(f.amount_usd) DESC) AS sales_rank
    FROM gold.fact_sales AS f
    JOIN gold.dim_store   AS s ON s.store_key   = f.store_key
    JOIN gold.dim_product AS p ON p.product_key = f.product_key
    GROUP BY s.store_name, p.category
) ranked
WHERE sales_rank <= 3
ORDER BY store_name, sales_rank, category;
-- DuckDB / Databricks SQL'de alt sorgu yerine: ... GROUP BY ... QUALIFY sales_rank <= 3

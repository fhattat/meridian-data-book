-- Soru 1: silver.bz_orders tablosunda kalemi olmayan siparişler hangileri?
-- Tuzak: INNER JOIN bu siparişleri sessizce kaybeder.
-- Çözüm: anti-join (LEFT JOIN + sağ anahtar IS NULL).
-- Test siparişlerini silmiyoruz; is_test sütunuyla gösteriyoruz ki ayrı ayrı incelenebilsin.
SELECT
    o.order_id,
    o.order_local_date,
    o.status_code,
    o.is_test
FROM silver.bz_orders AS o
LEFT JOIN silver.bz_order_items AS i
       ON i.order_id = o.order_id
WHERE i.order_id IS NULL
ORDER BY o.order_id;

-- Kısa yol (DuckDB / Databricks SQL): NOT EXISTS ile aynı sonuç
-- SELECT o.order_id FROM silver.bz_orders o
-- WHERE NOT EXISTS (SELECT 1 FROM silver.bz_order_items i WHERE i.order_id = o.order_id);
-- NOT IN kullanmayın: alt sorguda tek bir NULL order_id varsa sonuç boş döner.

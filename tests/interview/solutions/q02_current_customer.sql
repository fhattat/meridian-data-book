-- Soru 2: Her müşterinin gold.dim_customer içindeki güncel kaydını getirin.
-- Tuzak: SCD 2'de bir müşterinin birden çok satırı (sürümü) vardır.
-- Çözüm A (tercih edilen): is_current bayrağı.
SELECT customer_key, customer_id, valid_from, valid_to
FROM gold.dim_customer
WHERE is_current = TRUE
ORDER BY customer_id;

-- Çözüm B: bayrağa güvenmeden, en son valid_from'u seçmek.
-- İkisi aynı sonucu vermiyorsa SCD 2 yüklemesinde bir hata vardır; bu da iyi bir kalite testidir.
-- SELECT customer_key, customer_id, valid_from, valid_to
-- FROM (
--     SELECT d.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY valid_from DESC) AS rn
--     FROM gold.dim_customer d
-- ) x
-- WHERE rn = 1;
-- DuckDB / Databricks SQL'de alt sorgu yerine: ... QUALIFY ROW_NUMBER() OVER (...) = 1

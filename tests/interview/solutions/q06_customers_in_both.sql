-- Soru 6: Hem Meridian üyesi hem Bazaarly kullanıcısı olan kaç kişi var?
-- Tuzak: E-postada büyük-küçük harf ve boşluk farkı; test kayıtları.
-- Çözüm: silver.customer_xref zaten normalize e-posta (email_norm) üzerinden kurulmuştur.
-- Test kayıtlarını NOT EXISTS ile dışarıda bırakıyoruz (NOT IN, NULL yüzünden boş dönebilir).
SELECT COUNT(DISTINCT x.email_norm) AS people_in_both
FROM silver.customer_xref AS x
WHERE x.mm_member_id IS NOT NULL
  AND x.bz_user_id   IS NOT NULL
  AND NOT EXISTS (
        SELECT 1
        FROM silver.customers AS c
        WHERE c.email_norm = x.email_norm
          AND c.is_test = TRUE
  );

-- xref tablosu yoksa aynı soru silver.customers'tan:
-- SELECT COUNT(*) FROM (
--     SELECT lower(trim(email_norm)) AS e
--     FROM silver.customers
--     WHERE is_test = FALSE
--     GROUP BY lower(trim(email_norm))
--     HAVING SUM(CASE WHEN customer_type = 'member' THEN 1 ELSE 0 END) > 0
--        AND SUM(CASE WHEN customer_type = 'user'   THEN 1 ELSE 0 END) > 0
-- ) t;

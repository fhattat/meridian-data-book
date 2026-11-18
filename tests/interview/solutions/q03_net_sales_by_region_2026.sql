-- Soru 3: 2026'da her Census bölgesinin net satışı ne kadar?
-- Tuzak: Bazaarly'nin tek "Bazaarly Online" mağazası bir Census bölgesine ait değildir.
-- Net satış = SUM(gold.fact_sales.amount_usd): test ve iptaller zaten fact'te yok,
-- iadeler eksi satır olarak toplamı azaltır (kanonik tanım, Ek F ve metrics/sales.yaml).
-- Savunmacı LEFT JOIN: mağaza anahtarı eksik satır kaybolmasın.
SELECT
    COALESCE(s.region, 'Online (Bazaarly)') AS region,
    ROUND(SUM(f.amount_usd), 2)             AS net_sales_usd_2026
FROM gold.fact_sales AS f
JOIN gold.dim_date AS d
  ON d.date_key = f.date_key
LEFT JOIN gold.dim_store AS s
  ON s.store_key = f.store_key
WHERE d.year = 2026
GROUP BY COALESCE(s.region, 'Online (Bazaarly)')
ORDER BY net_sales_usd_2026 DESC;
-- Kontrol: Bu sorgunun toplamı, control_totals.json'daki 2026 MM + BZ toplamına eşit olmalı.

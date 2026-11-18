-- Soru 5: Başlık toplamı kalemlerinin toplamını tutmayan siparişleri listeleyin.
-- Tuzak: Kuruş yuvarlaması; kalemi hiç olmayan siparişin toplamı NULL değil 0'dır.
-- Çözüm: Kalemleri önce sipariş düzeyinde toplayın, sonra başlıkla karşılaştırın.
-- Aynı para biriminde karşılaştırıyoruz (original), kur farkı karışmasın (Bölüm 10 kuralı).
WITH lines AS (
    SELECT order_id, SUM(amount_original) AS lines_total
    FROM silver.bz_order_items
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.order_total_original                              AS header_total,
    COALESCE(l.lines_total, 0)                          AS lines_total,
    ROUND(o.order_total_original - COALESCE(l.lines_total, 0), 2) AS diff
FROM silver.bz_orders AS o
LEFT JOIN lines AS l
       ON l.order_id = o.order_id
WHERE o.is_test = FALSE
  AND ABS(o.order_total_original - COALESCE(l.lines_total, 0)) > 0.01
ORDER BY ABS(o.order_total_original - COALESCE(l.lines_total, 0)) DESC;
-- Yanlış: başlığı kalemlere JOIN edip SUM(order_total_original) almak; her başlık kalem sayısı kadar tekrar toplanır.

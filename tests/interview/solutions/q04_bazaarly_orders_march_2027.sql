-- Soru 4: Mart 2027'de Bazaarly'de kaç sipariş verildi?
-- Tuzak: Kalem sayısı sipariş sayısı değildir; test siparişleri sayılmaz.
-- "Verilen sipariş" iptal edilenleri de içerir (sipariş verilmiş, sonra iptal edilmiştir).
-- Soru net satışa giden siparişleri soruyorsa ikinci sütunu kullanın; cevabınızda hangisini
-- saydığınızı söyleyin.
-- Ay sınırı order_local_date ile (America/New_York iş günü), UTC zaman damgasıyla değil.
SELECT
    COUNT(DISTINCT o.order_id) AS orders_placed,
    COUNT(DISTINCT CASE WHEN o.status_code <> 'cancelled' THEN o.order_id END) AS orders_not_cancelled
FROM silver.bz_orders AS o
WHERE o.is_test = FALSE
  AND o.order_local_date >= '2027-03-01'
  AND o.order_local_date <  '2027-04-01';
-- Yanlış: silver.bz_order_items üzerinde COUNT(*) — her kalemi bir sipariş sayar.

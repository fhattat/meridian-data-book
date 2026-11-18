-- Soru 8: Bronze ile silver arasında kaybolan POS satırı var mı?
-- Tuzak: Test kayıtları silver'da is_test ile işaretlenir, silinmez; yani "kayıp" sayılmaz.
-- Bronze'da her şey metindir ve boşluk içerebilir; anahtarı silver'daki gibi normalize edin.
-- Çözüm: bronze'daki satır anahtarları EXCEPT silver'daki satır anahtarları.
SELECT TRIM(b.RECEIPT_NO) AS receipt_no,
       CAST(TRIM(b.LINE_NO) AS INTEGER) AS line_no
FROM bronze.mm_pos_named AS b
WHERE b.rec_type = 'L'
EXCEPT
SELECT p.receipt_no, p.line_no
FROM silver.pos_lines AS p
ORDER BY receipt_no, line_no;
-- Sonuç boş değilse her farkı bir kategoriye ayırın: karantinada mı (quality.quarantine),
-- dönüşüm hatası mı (tip çevrimi), yoksa açıklanamayan kayıp mı? Yalnızca sonuncusu bir arızadır.
-- Ters yönü de kontrol edin: silver'da olup bronze'da olmayan satır, çift yükleme belirtisidir.

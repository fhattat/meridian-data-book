# Ek C — SQL alıştırmalarının çözümleri

> Bu klasördeki bütün veriler, şirket adları ve dosyalar sentetiktir; hiçbir gerçek kişiye ait değildir.
> All data, company names and files here are synthetic and belong to no real person.

## Önce kendiniz çözün

Ek C'deki sekiz soruyu **AI'sız**, her biri için en fazla 15 dakikayla çözün. Sonra buradaki çözümle karşılaştırın. Mülakatta da AI olmayacak; burada kazandığınız şey hız değil, tuzağı görme alışkanlığı.

## Dosyalar

| Soru | Dosya | Tuzak |
|---|---|---|
| 1 | `solutions/q01_orders_without_items.sql` | `NOT IN` ve NULL; anti-join |
| 2 | `solutions/q02_current_customer.sql` | SCD 2'de birden fazla satır |
| 3 | `solutions/q03_net_sales_by_region_2026.sql` | Bazaarly Online bir bölgede değil (NULL) |
| 4 | `solutions/q04_bazaarly_orders_march_2027.sql` | `COUNT(DISTINCT)`, iptal ve test siparişleri |
| 5 | `solutions/q05_header_vs_lines.sql` | Kalemi olmayan sipariş, kuruş toleransı |
| 6 | `solutions/q06_customers_in_both.sql` | E-posta normalizasyonu, test kayıtları |
| 7 | `solutions/q07_top3_categories_per_store.sql` | `RANK` ve `ROW_NUMBER` farkı (eşitlik) |
| 8 | `solutions/q08_bronze_vs_silver_pos.sql` | Boşluklu metin anahtarlar; test kayıtları silinmez, işaretlenir |

`fixture.sql` küçük bir test verisi kurar; her tuzak en az bir satırla temsil edilir. `test_interview_solutions.py` her çözümü bu veride çalıştırıp beklenen cevapla karşılaştırır.

## Çalıştırma

Depo kökünden:

```bash
pytest tests/interview -q
```

Testler DuckDB ile çalışır. DuckDB kurulu değilse Python'un yerleşik `sqlite3` modülüne geçer; çözümler bu yüzden DuckDB, Databricks SQL ve SQLite'ta aynı çalışan taşınabilir SQL ile yazıldı. `QUALIFY` gibi kısa yazımlar dosyalardaki yorumlarda.

Gerçek veride denemek için:

```bash
duckdb data/meridian.duckdb < tests/interview/solutions/q03_net_sales_by_region_2026.sql
```

Databricks'te tablo adlarının önüne katalog adını ekleyin (`meridian_dev.gold.fact_sales` gibi).

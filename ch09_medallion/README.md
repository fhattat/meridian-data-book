# Bölüm 9 — Depolama ve Medallion ile dönüşüm
### Chapter 9 — Storage and transformation with Medallion

QR-09 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch09_medallion/clean_silver.py --env local
```

## Dosyalar / Files

- [clean_silver.py](clean_silver.py)
- [engines/clean_pandas.py](engines/clean_pandas.py)
- [engines/clean_polars.py](engines/clean_polars.py)
- [engines/clean_pyspark.py](engines/clean_pyspark.py)
- [engines/compare_outputs.py](engines/compare_outputs.py)
- [sample_summary.json](sample_summary.json)
- [sql/silver/duckdb/00_helpers.sql](sql/silver/duckdb/00_helpers.sql)
- [sql/silver/duckdb/10_stores_geo.sql](sql/silver/duckdb/10_stores_geo.sql)
- [sql/silver/duckdb/20_products.sql](sql/silver/duckdb/20_products.sql)
- [sql/silver/duckdb/30_customers.sql](sql/silver/duckdb/30_customers.sql)
- [sql/silver/duckdb/40_pos.sql](sql/silver/duckdb/40_pos.sql)
- [sql/silver/duckdb/50_bz_orders.sql](sql/silver/duckdb/50_bz_orders.sql)
- [sql/silver/duckdb/60_inventory_campaigns.sql](sql/silver/duckdb/60_inventory_campaigns.sql)
- [sql/silver/duckdb/70_xref.sql](sql/silver/duckdb/70_xref.sql)
- [tool_clean.json](tool_clean.json)

Veri sentetiktir / all data is synthetic (see the main README).

# Bölüm 6 — Platform ve araç seçimi
### Chapter 6 — Choosing a platform and tools

QR-06 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch06_platform/benchmark_engines.py                      # reads data/layers/silver/pos_lines.parquet
python ch06_platform/benchmark_engines.py sample.parquet --synthetic 1000000   # without the pipeline
```

## Dosyalar / Files

- [benchmark_engines.py](benchmark_engines.py)
- [pyspark_same_query.py](pyspark_same_query.py)

Veri sentetiktir / all data is synthetic (see the main README).

# Chapter 6 — Choosing a platform and tools

QR-06 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python ch06_platform/benchmark_engines.py                                  # reads data/layers/silver/pos_lines.parquet
python ch06_platform/benchmark_engines.py sample.parquet --synthetic 1000000   # without the pipeline
```

## Files

- [benchmark_engines.py](benchmark_engines.py)
- [pyspark_same_query.py](pyspark_same_query.py)

All data is synthetic (see the main README).

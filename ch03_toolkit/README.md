# Chapter 3 — Toolkit: environment, SQL and Python

QR-03 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python data/generate_data.py --size small --seed 2027 --out data/raw
python ch03_toolkit/load_sample.py
python ch03_toolkit/count_legacy_sql_patterns.py
```

## Files

- [count_legacy_sql_patterns.py](count_legacy_sql_patterns.py)
- [load_sample.py](load_sample.py)
- [same_question_four_tools.py](same_question_four_tools.py)

All data is synthetic (see the main README).

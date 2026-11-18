# Chapter 7 — Knowing the source systems and data profiling

QR-07 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python ch07_profiling/profile_source.py data/raw/bazaarly/csv/bz_products.csv --guide ref/source_guide.yaml
python ch07_profiling/profile_source.py --env local   # default sources, drafts in reports/drafts/
```

## Files

- [manual_profile.sql](manual_profile.sql)
- [profile_source.py](profile_source.py)
- [tool_profile.json](tool_profile.json)

All data is synthetic (see the main README).

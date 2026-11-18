# Chapter 10 — Data quality and reliable pipelines

QR-10 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python ch10_quality/quality_checks.py --env local   # exit 1 on a critical failure
```

## Files

- [quality_checks.py](quality_checks.py)
- [rules.yaml](rules.yaml)

All data is synthetic (see the main README).

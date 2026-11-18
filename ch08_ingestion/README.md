# Chapter 8 — Ingestion: ETL, ELT and real life

QR-08 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python ch08_ingestion/ingest_to_bronze.py --env local --source mm_pos   # first run: resend skipped, 20260209 missing
python ch08_ingestion/ingest_to_bronze.py --env local --source all
python ch08_ingestion/stream_simulator.py
```

## Files

- [fx_api_mock.py](fx_api_mock.py)
- [ingest_to_bronze.py](ingest_to_bronze.py)
- [stream_simulator.py](stream_simulator.py)
- [tool_ingest.json](tool_ingest.json)

All data is synthetic (see the main README).

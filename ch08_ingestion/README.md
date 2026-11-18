# Bölüm 8 — Veri alımı: ETL, ELT ve gerçek hayat
### Chapter 8 — Ingestion: ETL, ELT and real life

QR-08 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch08_ingestion/ingest_to_bronze.py --env local --source mm_pos   # first run: resend skipped, 20260209 missing
python ch08_ingestion/ingest_to_bronze.py --env local --source all
python ch08_ingestion/stream_simulator.py
```

## Dosyalar / Files

- [fx_api_mock.py](fx_api_mock.py)
- [ingest_to_bronze.py](ingest_to_bronze.py)
- [stream_simulator.py](stream_simulator.py)
- [tool_ingest.json](tool_ingest.json)

Veri sentetiktir / all data is synthetic (see the main README).

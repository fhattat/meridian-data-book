# Bölüm 10 — Veri kalitesi ve güvenilir pipeline
### Chapter 10 — Data quality and reliable pipelines

QR-10 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch10_quality/quality_checks.py --env local   # exit 1 on a critical failure
```

## Dosyalar / Files

- [quality_checks.py](quality_checks.py)
- [rules.yaml](rules.yaml)

Veri sentetiktir / all data is synthetic (see the main README).

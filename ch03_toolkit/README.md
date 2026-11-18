# Bölüm 3 — Araç çantası: çalışma ortamı, SQL ve Python
### Chapter 3 — Toolkit: environment, SQL and Python

QR-03 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python data/generate_data.py --size small --seed 2027 --out data/raw
python ch03_toolkit/load_sample.py
python ch03_toolkit/count_legacy_sql_patterns.py
```

## Dosyalar / Files

- [count_legacy_sql_patterns.py](count_legacy_sql_patterns.py)
- [load_sample.py](load_sample.py)
- [same_question_four_tools.py](same_question_four_tools.py)

Veri sentetiktir / all data is synthetic (see the main README).

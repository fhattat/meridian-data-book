# Bölüm 7 — Kaynak sistemleri tanımak ve veri profilleme
### Chapter 7 — Knowing the source systems and data profiling

QR-07 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch07_profiling/profile_source.py data/raw/bazaarly/csv/bz_products.csv --guide ref/source_guide.yaml
python ch07_profiling/profile_source.py --env local   # default sources, drafts in reports/drafts/
```

## Dosyalar / Files

- [manual_profile.sql](manual_profile.sql)
- [profile_source.py](profile_source.py)
- [tool_profile.json](tool_profile.json)

Veri sentetiktir / all data is synthetic (see the main README).

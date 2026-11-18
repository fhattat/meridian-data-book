# Bölüm 18 — Uçtan uca proje: Meridian Market’in veri ve AI platformu
### Chapter 18 — End-to-end project: Meridian Market's data and AI platform

QR-18 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python run_pipeline.py --env local --size small
python ch18_capstone/board_question.py
```

## Dosyalar / Files

- [PORTFOLIO_README_TEMPLATE.md](PORTFOLIO_README_TEMPLATE.md)
- [architecture.mmd](architecture.mmd)
- [board_question.py](board_question.py)
- [board_question.sql](board_question.sql)
- [rerun_experiment.sh](rerun_experiment.sh)
- [support_assistant_trace.txt](support_assistant_trace.txt)

Veri sentetiktir / all data is synthetic (see the main README).

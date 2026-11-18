# Chapter 18 — End-to-end project: Meridian Market's data and AI platform

QR-18 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python run_pipeline.py --env local --size small
python ch18_capstone/board_question.py
```

## Files

- [PORTFOLIO_README_TEMPLATE.md](PORTFOLIO_README_TEMPLATE.md)
- [architecture.mmd](architecture.mmd)
- [board_question.py](board_question.py)
- [board_question.sql](board_question.sql)
- [rerun_experiment.sh](rerun_experiment.sh)
- [support_assistant_trace.txt](support_assistant_trace.txt)

All data is synthetic (see the main README).

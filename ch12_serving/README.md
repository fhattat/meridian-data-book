# Chapter 12 — Serving data: BI, ML and AI consumers

QR-12 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python ch12_serving/export_features.py --env local
python ch12_serving/build_rag_index.py --env local
python ch12_serving/build_rag_index.py --query "order still preparing"
```

## Files

- [build_rag_index.py](build_rag_index.py)
- [data_assistant_system_prompt.txt](data_assistant_system_prompt.txt)
- [export_features.py](export_features.py)

All data is synthetic (see the main README).

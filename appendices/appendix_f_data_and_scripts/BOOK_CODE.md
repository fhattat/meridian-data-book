# Appendix F — Data sets and script repository (QR index)

## Code from the book

Every code block of this chapter, in book order, under the book's section headings.
Runnable files are in this folder; for scripts printed as "(shortened)" in the book, the full version is the file here.

### What is this appendix for?

**Code F.1**

```bash
git clone https://github.com/fhattat/meridian-data-book && cd meridian-data-book
pip install -r requirements.txt
python data/generate_data.py --size small --seed 2027 --out data/raw   # or: make data
python run_pipeline.py --env local --size small                      # or: make all
```

### Repository layout and script index

**Code F.2**

```text
meridian-data-book/
├── README.md  REFERENCES.md  CLAUDE.md  RULES.md  Makefile  requirements.txt
├── run_pipeline.py  databricks.yml  pipelines.yaml  glossary.yaml  CODEOWNERS
├── data/        generate_data.py, raw/, layers/
├── ref/  contracts/  governance/  metadata/  metrics/  products/
├── jobs/  runbooks/  lib/  prompts/  reports/  tests/  appendices/
└── ch01_what_is_de/ … ch20_future/   (chapter folders: README.md, BOOK_CODE.md, scripts)
```

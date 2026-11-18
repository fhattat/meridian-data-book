# Appendix F — Data sets and script repository (QR index)

## Code from the book

Every code block of this chapter, in book order, under the book's section headings.
Runnable files are in this folder; for scripts printed as "(shortened)" in the book, the full version is the file here.

### What is this appendix for?

**Code F.1**

```bash
git clone <repo-url> meridian-data-book && cd meridian-data-book
pip install -r requirements.txt
python data/generate_data.py --size small --seed 2027 --out data/raw   # or: make data
python run_pipeline.py --env local --size small                      # or: make all
```

### Repository layout and script index

**Code F.2**

```text
meridian-data-book/
├── README.md  CLAUDE.md  Makefile  requirements.txt
├── run_pipeline.py  databricks.yml  pipelines.yaml  glossary.yaml  CODEOWNERS
├── data/        generate_data.py, raw/, layers/
├── ref/  contracts/  governance/  metadata/  metrics/  products/
├── jobs/  runbooks/  lib/  prompts/  reports/  tests/
└── ch03_toolkit/ … ch19_career/   (chapter folders)
```

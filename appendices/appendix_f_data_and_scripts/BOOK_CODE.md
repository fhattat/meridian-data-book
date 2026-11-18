# Ek F — Veri setleri ve script deposu (QR dizini)

## Code from the book

Every code block of this chapter, in book order, under the book's section headings (Turkish, as printed).
Runnable files are in this folder; for scripts printed as "(shortened)" the full version is the file here.
Bu dosya bölümdeki bütün kod bloklarını kitaptaki sırasıyla ve alt bölüm başlıklarıyla verir.

### Bu ek ne için?

> Hızlı başlangıç (ücretsiz yol, DuckDB):

**Code Ek F.1**

```bash
git clone <repo-url> meridian-data-book && cd meridian-data-book
pip install -r requirements.txt
python data/generate_data.py --size small --seed 2027 --out data/raw   # or: make data
python run_pipeline.py --env local --size small                      # or: make all
```

### Depo yapısı ve script dizini

> Depo (meridian-data-book) bölüm klasörlerine ayrılır. Ortak kod lib/ altında, kök dizinde ise bütün kitabı birbirine bağlayan dosyalar durur. Google Drive’da da aynı bölüm klasörleri var; her klasörde o bölümün veri seti ve script’i bulunur.

**Code Ek F.2**

```text
meridian-data-book/
├── README.md  CLAUDE.md  Makefile  requirements.txt
├── run_pipeline.py  databricks.yml  pipelines.yaml  glossary.yaml  CODEOWNERS
├── data/        generate_data.py, raw/, layers/
├── ref/  contracts/  governance/  metadata/  metrics/  products/
├── jobs/  runbooks/  lib/  prompts/  reports/  tests/
└── ch03_toolkit/ … ch19_career/   (chapter folders)
```

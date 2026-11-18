# Bölüm 14 — Metadata, katalog, lineage ve güvenlik
### Chapter 14 — Metadata, catalog, lineage and security

QR-14 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch14_governance/extract_metadata.py --env local --schema gold
python ch14_governance/rls_test.py
```

## Dosyalar / Files

- [extract_metadata.py](extract_metadata.py)
- [grants_and_masking_databricks.sql](grants_and_masking_databricks.sql)
- [lineage.mmd](lineage.mmd)
- [masked_view.sql](masked_view.sql)
- [rls_test.py](rls_test.py)
- [sample_metadata_silver.customers.yaml](sample_metadata_silver.customers.yaml)
- [tool_catalog.json](tool_catalog.json)
- [unity_catalog_comments.sql](unity_catalog_comments.sql)

Veri sentetiktir / all data is synthetic (see the main README).

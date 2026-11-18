# Bölüm 11 — Veri modelleme: star schema ve ötesi
### Chapter 11 — Data modeling: star schema and beyond

QR-11 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch11_modeling/build_gold.py --env local
python ch11_modeling/model_checks.py --env local
python ch11_modeling/text_to_sql_eval.py --env local --layer gold   # needs ask_llm()
```

## Dosyalar / Files

- [build_gold.py](build_gold.py)
- [gold_grain.md](gold_grain.md)
- [model_checks.py](model_checks.py)
- [questions.yaml](questions.yaml)
- [reference_answers.sql](reference_answers.sql)
- [sql/gold/00_dim_date.sql](sql/gold/00_dim_date.sql)
- [sql/gold/10_dim_store.sql](sql/gold/10_dim_store.sql)
- [sql/gold/20_dim_product.sql](sql/gold/20_dim_product.sql)
- [sql/gold/30_dim_customer.sql](sql/gold/30_dim_customer.sql)
- [sql/gold/40_dim_other.sql](sql/gold/40_dim_other.sql)
- [sql/gold/50_fact_sales.sql](sql/gold/50_fact_sales.sql)
- [sql/gold/60_fact_order_process.sql](sql/gold/60_fact_order_process.sql)
- [sql/gold/70_fact_snapshots.sql](sql/gold/70_fact_snapshots.sql)
- [sql/gold/90_security.sql](sql/gold/90_security.sql)
- [sql/gold/95_serving_views.sql](sql/gold/95_serving_views.sql)
- [text_to_sql_eval.py](text_to_sql_eval.py)
- [tool_modeling.json](tool_modeling.json)

Veri sentetiktir / all data is synthetic (see the main README).

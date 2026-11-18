# Bölüm 12 — Veriyi sunmak: BI, ML ve AI tüketicileri
### Chapter 12 — Serving data: BI, ML and AI consumers

QR-12 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch12_serving/export_features.py --env local
python ch12_serving/build_rag_index.py --env local
python ch12_serving/build_rag_index.py --query "order still preparing"
```

## Dosyalar / Files

- [build_rag_index.py](build_rag_index.py)
- [data_assistant_system_prompt.txt](data_assistant_system_prompt.txt)
- [export_features.py](export_features.py)

Veri sentetiktir / all data is synthetic (see the main README).

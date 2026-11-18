# Bölüm 13 — Orkestrasyon, izleme ve arıza yönetimi
### Chapter 13 — Orchestration, monitoring and incident management

QR-13 · Kitabın deposu / book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: bölümdeki bütün kodlar, kitaptaki sırası ve alt bölüm başlıklarıyla / every code block of the chapter in book order.

## Çalıştırma / Run

Depo kökünden, `export PYTHONPATH=.` ile (Makefile bunu kendisi yapar) / from the repository root:

```bash
python ch13_operations/check_pipeline_logs.py data/raw/ops/pipeline_logs/2027-04-15.log --no-append
python ch13_operations/big_review.py
```

## Dosyalar / Files

- [airflow_nightly_meridian.py](airflow_nightly_meridian.py)
- [big_review.py](big_review.py)
- [check_pipeline_logs.py](check_pipeline_logs.py)
- [incident_log.yaml](incident_log.yaml)
- [sample_alert.txt](sample_alert.txt)
- [sample_incident_log_excerpt.log](sample_incident_log_excerpt.log)
- [stakeholder_email_template.txt](stakeholder_email_template.txt)
- [tool_incident.json](tool_incident.json)
- [tool_review.json](tool_review.json)

Veri sentetiktir / all data is synthetic (see the main README).

# Chapter 13 — Orchestration, monitoring and incident management

QR-13 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python ch13_operations/check_pipeline_logs.py data/raw/ops/pipeline_logs/2027-04-15.log --no-append
python ch13_operations/big_review.py
```

## Files

- [airflow_nightly_meridian.py](airflow_nightly_meridian.py)
- [big_review.py](big_review.py)
- [check_pipeline_logs.py](check_pipeline_logs.py)
- [incident_log.yaml](incident_log.yaml)
- [sample_alert.txt](sample_alert.txt)
- [sample_incident_log_excerpt.log](sample_incident_log_excerpt.log)
- [stakeholder_email_template.txt](stakeholder_email_template.txt)
- [tool_incident.json](tool_incident.json)
- [tool_review.json](tool_review.json)

All data is synthetic (see the main README).

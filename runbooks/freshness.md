# runbooks/freshness.md - gold.fact_sales is late (Chapter 13.3)

## Purpose
The management dashboard must show yesterday's sales by 06:00 New York time (SLO). This runbook is
the first step when the freshness alert fires.

## Steps (in order)
1. Read the nightly job status: which task failed or is still running? (Databricks Jobs UI or reports/run_<date>.json)
2. Scan the night's log with the incident tool: `python ch13_operations/check_pipeline_logs.py <log>`.
3. If the cause is transient (timeout fixed on retry): re-run only the failed task, after approval.
4. If the cause is schema or data: do not re-run; open an incident (incident_log.yaml) and tell the source owner.
5. Tell Marcus (dashboard owner) what is late, why, and when to expect it (template: ch13_operations/stakeholder_email_template.txt).

## Limits
Never publish gold by hand or skip the quality gate to "make the dashboard green".

## Done when
The dashboard shows yesterday, the incident record has a cause, and the alert is closed.

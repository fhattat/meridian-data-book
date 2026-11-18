# Chapter 13 — Orchestration, monitoring and incident management

## Code from the book

Every code block of this chapter, in book order, under the book's section headings.
Runnable files are in this folder; for scripts printed as "(shortened)" in the book, the full version is the file here.

### 13.1 From cron to an orchestrator: Databricks Jobs, Airflow and Dagster

**Code 13.1**

```yaml
# jobs/nightly_meridian.yml (simplified)
name: nightly_meridian
schedule: "0 0 2 * * ?"        # every night at 02:00 New York time
timezone_id: America/New_York  # without it the scheduler assumes UTC
max_retries: 2                 # retries per step
tasks:
  - key: ingest
    python_file: ch08_ingestion/ingest_to_bronze.py
    parameters: ["--env", "databricks"]
  - key: clean_silver
    depends_on: [ingest]
    python_file: ch09_medallion/clean_silver.py
  - key: quality_gate
    depends_on: [clean_silver]
    python_file: ch10_quality/quality_checks.py   # exit code 1 = stop
  - key: build_gold
    depends_on: [quality_gate]
    python_file: ch11_modeling/build_gold.py
  - key: model_checks
    depends_on: [build_gold]
    python_file: ch11_modeling/model_checks.py   # read-only; a failure is reported, the dashboard still refreshes
  - key: refresh_dashboard
    depends_on: [build_gold]
```

**Code 13.2**

```python
import pendulum
from airflow import DAG                           # recommended in Airflow 3: from airflow.sdk import DAG
from airflow.operators.bash import BashOperator  # in Airflow 3: airflow.providers.standard.operators.bash

with DAG("nightly_meridian", schedule="0 2 * * *",
         start_date=pendulum.datetime(2027, 1, 1, tz="America/New_York"), catchup=False,
         default_args={"retries": 2}) as dag:
    ingest = BashOperator(task_id="ingest", bash_command="python ch08_ingestion/ingest_to_bronze.py --env local")
    silver = BashOperator(task_id="clean_silver", bash_command="python ch09_medallion/clean_silver.py --env local")
    gate = BashOperator(task_id="quality_gate", bash_command="python ch10_quality/quality_checks.py --env local")
    gold = BashOperator(task_id="build_gold", bash_command="python ch11_modeling/build_gold.py --env local")
    checks = BashOperator(task_id="model_checks", bash_command="python ch11_modeling/model_checks.py --env local")
    ingest >> silver >> gate >> gold >> checks
```

### 13.2 Config-driven pipelines; Git, CI and environments

**Code 13.3**

```yaml
# pipelines.yaml (shortened)
defaults:
  freshness_hours: 26        # for the freshness SLI in 13.3
  owner: data-platform

sources:
  - name: mm_pos_raw
    mode: file
    path: meridian/pos/pos_*.csv   # root: data/raw/ (local) or /Volumes/meridian/raw/landing/
    format: {delimiter: ";", encoding: cp1252, header: false}
    contract: contracts/mm_pos_raw.yaml
    schedule: nightly
    owner: meridian-it
  - name: bz_orders_2027
    mode: file
    path: bazaarly/bz_orders_2027/*.csv
    format: {delimiter: ",", encoding: utf-8, header: true}
    contract: contracts/bz_orders.yaml
    schedule: nightly
    owner: bazaarly-app
  - name: bz_support_tickets
    mode: file
    path: bazaarly/bz_support_tickets.jsonl   # cumulative export, rewritten every hour
    format: {type: jsonl, encoding: utf-8}
    contract: contracts/bz_support_tickets.yaml
    schedule: hourly
    freshness_hours: 2
    owner: bazaarly-support
  - name: ref_fx_rates
    mode: api
    endpoint: fx_api_mock
    schedule: nightly
    freshness_hours: 72      # no rates on weekends
```

### 13.3 Job monitoring and data monitoring; SLI, SLO, SLA and actionable alerts

**Code 13.4**

```text
[CRITICAL] freshness: gold.fact_sales is 2 days behind (expected: 1)
Impact: the management dashboard and agg_sales_daily show yesterday's data.
Owner: data-platform (on call: Deniz)
First step: runbooks/freshness.md · last run: nightly_meridian, 2027-04-16 03:12
```

### 13.4 Incident review: where, why, seen before?

**Code 13.5**

```markdown
# Times are UTC. New York is UTC-4 in summer time: 06:10Z = 02:10 ET.
2027-04-16T06:10:12Z WARN  step=ingest source=ref_fx_rates msg="TimeoutError: fx_api_mock did not respond in 30s" attempt=1
2027-04-16T06:10:44Z INFO  step=ingest source=ref_fx_rates msg="retry succeeded" attempt=2
2027-04-16T06:35:03Z WARN  step=ingest source=bz_events msg="TimeoutError: read timed out" attempt=1
2027-04-16T06:35:31Z INFO  step=ingest source=bz_events msg="retry succeeded" attempt=2
2027-04-16T07:12:04Z ERROR step=bronze_to_silver_orders msg="KeyError: 'status_code'" attempt=3
2027-04-16T07:12:05Z INFO  step=quality_gate msg="skipped: upstream failed"
2027-04-16T07:12:05Z INFO  step=build_gold msg="skipped: upstream failed"
```

**Code 13.6**

```python
# ch13_operations/check_pipeline_logs.py (shortened)
import re, json, argparse, datetime as dt
from pathlib import Path
import yaml

LINE = re.compile(r'(?P<ts>\S+) (?P<level>\w+)\s+step=(?P<step>\S+)(?: source=(?P<source>\S+))? msg="(?P<msg>[^"]*)"(?: attempt=(?P<attempt>\d+))?')
CLASSES = [  # (class, pattern) — order matters
    ("transient", r"Timeout|ConnectionError|read timed out"),
    ("schema",    r"KeyError|column .* not found|cannot resolve|schema_gate: hold"),
    ("data",      r"quality_gate: critical|duplicate key|reconcile: diff"),
]

def classify(msg):
    for name, pattern in CLASSES:
        if re.search(pattern, msg, re.I):
            return name
    return "unknown"

def parse(log_path):
    events = []
    for raw in Path(log_path).read_text(encoding="utf-8").splitlines():
        m = LINE.match(raw)
        if m and m["level"] in ("WARN", "ERROR"):
            e = m.groupdict(); e["class"] = classify(e["msg"]); events.append(e)
    # a transient error is noise if the same step+source later succeeded
    healed = {(m["step"], m["source"]) for m in map(LINE.match, Path(log_path).read_text().splitlines())
              if m and "retry succeeded" in m["msg"]}
    for e in events:
        e["noise"] = e["class"] == "transient" and (e["step"], e["source"]) in healed
    return events

def similar(event, incidents):
    """Past records with the same class and the same step (or a shared keyword)."""
    words = set(re.findall(r"[a-z_]{4,}", event["msg"].lower()))
    hits = []
    for inc in incidents:
        score = (inc.get("class") == event["class"]) + (inc.get("step") == event["step"])
        score += len(words & set(inc.get("keywords", [])))
        if score >= 2:
            hits.append((score, inc["id"], inc.get("summary") or inc.get("symptom")))
    return sorted(hits, reverse=True)[:3]

def run(log_path, incident_log="ch13_operations/incident_log.yaml", report_dir="reports", append=True):
    incidents = yaml.safe_load(Path(incident_log).read_text(encoding="utf-8")) or []
    events = parse(log_path)
    blocking = [e for e in events if e["level"] == "ERROR"]
    findings = [{**e, "similar": similar(e, incidents)} for e in blocking]
    summary = {
        "log": str(log_path),
        "noise_count": sum(e["noise"] for e in events),
        "blocking": findings,
        "status": "failed" if findings else "ok",
    }
    if findings and append:  # new records are added as open; a human fills in the root cause
        f = findings[0]
        incidents.append({
            "id": f"INC-{dt.date.today():%Y%m%d}-{len(incidents)+1:02d}",
            "opened_at": f["ts"], "step": f["step"], "class": f["class"],
            "symptom": f["msg"], "status": "open", "root_cause": None,
            "keywords": sorted(set(re.findall(r"[a-z_]{4,}", f["msg"].lower()))),
        })
        Path(incident_log).write_text(yaml.safe_dump(incidents, allow_unicode=True, sort_keys=False), encoding="utf-8")
    Path(report_dir).mkdir(exist_ok=True)
    Path(report_dir, "incident_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("log_path"); p.add_argument("--env", default="local")
    print(json.dumps(run(p.parse_args().log_path), indent=2))
```

**Code 13.7**

```text
To: Marcus, finance reporting team
Subject: The management dashboard was 20 minutes late this morning; the figures are current
Summary: Bazaarly orders of April 15 could not be processed overnight. As of 07:50 the dashboard
is current, April 15 included. No figure changed; only the time was late.
Why: A column was renamed in the source system. We are extending the check so that the same
situation does not stop the dashboard on another night.

To: Bazaarly application team (owner of bz_orders)
Subject: 'status_code' -> 'status' change in the bz_orders daily file
From the April 15 file on, the column name has changed. In the data contract (contracts/bz_orders.yaml)
this column is defined as 'status_code'. Is the change permanent? If so, let's update the contract.
For future changes we propose a two-week notice period.
```

### 13.5 The knowledge layer: the incident log

**Code 13.8**

```yaml
- id: INC-20251129-01
  opened_at: 2025-11-29T07:05:00Z
  closed_at: 2025-11-29T11:20:00Z
  step: ingest
  source: mm_pos_raw
  class: data
  summary: The Black Friday POS file arrived a second time the next day
  symptom: "November 28 sales showed up doubled"
  root_cause: The store system resent the file with a `_resend` suffix
  temp_fix: The rows of the second file were deleted by hand in the old warehouse
  permanent_fix: Not written. The same error came back on the new platform in March 2027; fixed with idempotent loading via _row_hash (Chapter 8)
  keywords: [duplicate, resend, pos, idempotency]
  status: closed

- id: INC-20270212-01
  opened_at: 2027-02-12T08:20:00Z
  closed_at: 2027-02-12T09:40:00Z
  step: bazaarly_legacy_report
  source: bz_orders_2027
  class: data
  summary: Orders with channel code 50 showed an empty channel in Bazaarly's legacy dashboard
  root_cause: Bazaarly opened a new sales channel without updating the code table
  temp_fix: The Bazaarly team showed the channel as "unknown" in the dashboard
  permanent_fix: Not written; the code's meaning was never documented (open question in Chapter 7, unmapped-code rule in Chapter 10)
  keywords: [channel_code, unmapped, mapping]
  status: monitoring

- id: INC-20260212-01
  opened_at: 2026-02-12T08:15:00Z
  step: ingest
  source: mm_pos_raw
  class: data
  summary: The February 9 POS file was missing; it was found three days later in the wrong folder
  root_cause: The delivery script wrote the wrong target folder
  permanent_fix: Not written; added in 2027 as the missing-day report and backfill (Chapter 8)
  keywords: [missing, late, backfill, pos]
  status: closed

- id: INC-20270416-07
  opened_at: 2027-04-16T07:12:04Z
  closed_at: 2027-04-16T11:50:00Z
  step: bronze_to_silver_orders
  source: bz_orders_2027
  class: schema
  summary: The status_code column was renamed to status at the source
  symptom: "KeyError: 'status_code'"
  root_cause: >
    The Bazaarly app team renamed the column starting with the April 15 file;
    schema_gate was attached only to the POS sources.
  temp_fix: An alias was added to the contract and the DAG was re-run from the failed step
  permanent_fix: schema_gate attached to every source in pipelines.yaml; two-week notice rule
  keywords: [keyerror, status_code, schema, rename, drift]
  related: [INC-20270212-01]
  impact: "Dashboard current at 07:50; SLO missed, SLA kept"
  status: closed
```

### 13.6 The big review: unused tables, slow queries, cost

**Code 13.9**

```python
# ch13_operations/big_review.py (shortened)
import json, argparse
import duckdb

def run(history_csv="data/raw/ops/query_history.csv", db="data/meridian.duckdb", days=90, top_n=5):
    con = duckdb.connect(db, read_only=True)
    con.execute(f"""
        CREATE TEMP VIEW qh AS
        SELECT *, CAST(started_at AS TIMESTAMP) AS ts
        FROM read_csv('{history_csv}', header = true)
        WHERE CAST(started_at AS TIMESTAMP) >= now() - INTERVAL {days} DAY
    """)
    # tables per query, separated by ';': 'gold.fact_sales;gold.dim_date'
    con.execute("""
        CREATE TEMP VIEW qh_tables AS
        SELECT query_id, cost_usd, trim(unnest(string_split(tables, ';'))) AS table_name FROM qh
    """)
    catalog = con.execute("""
        SELECT table_schema || '.' || table_name AS t FROM information_schema.tables
        WHERE table_schema IN ('bronze', 'silver', 'gold')
    """).fetchall()
    used = {r[0] for r in con.execute("SELECT DISTINCT table_name FROM qh_tables").fetchall()}
    unused = sorted(t for (t,) in catalog if t not in used and not t.startswith("bronze."))

    total = con.execute("SELECT sum(cost_usd) FROM qh").fetchone()[0] or 0
    top = con.execute(f"""
        SELECT query_id, user_name, round(cost_usd, 2) AS cost_usd, duration_ms
        FROM qh ORDER BY cost_usd DESC LIMIT {top_n}
    """).fetchdf()
    slow_repeated = con.execute("""
        SELECT tables, count(*) AS runs, round(median(duration_ms) / 1000, 1) AS median_s
        FROM qh GROUP BY tables HAVING count(*) >= 20 AND median(duration_ms) > 60000
        ORDER BY runs DESC
    """).fetchdf()
    by_table = con.execute("""
        SELECT table_name, round(sum(cost_usd), 2) AS cost_usd, count(DISTINCT query_id) AS queries
        FROM qh_tables GROUP BY table_name ORDER BY cost_usd DESC
    """).fetchdf()
    return {
        "window_days": days,
        "unused_tables": unused,
        "top_queries_cost_share": round(float(top["cost_usd"].sum()) / total, 3) if total else None,
        "top_queries": top.to_dict("records"),
        "slow_repeated": slow_repeated.to_dict("records"),
        "cost_by_table": by_table.head(15).to_dict("records"),
        "note": "Recommendation only. Dropping a table or stopping its refresh is the table owner's decision.",
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--env", default="local")
    print(json.dumps(run(), indent=2, default=str))
```

### 13.8 Script → tool: incident and review

**Code 13.10**

```json
{
  "name": "incident",
  "description": "Reads one nightly pipeline log, separates healed transient errors from blocking errors, finds similar past incidents in incident_log.yaml and returns a draft incident report. Never fixes or reruns anything.",
  "parameters": {
    "type": "object",
    "properties": {
      "log_path": {"type": "string", "description": "Path to the log file, e.g. pipeline_logs/2027-04-15.log"},
      "append": {"type": "boolean", "default": true, "description": "If true, adds one new incident with status 'open'. Root cause stays empty for a human to fill."}
    },
    "required": ["log_path"]
  },
  "returns": "JSON: status, noise_count, blocking[] with class and similar incidents"
}
```

**Code 13.11**

```json
{
  "name": "review",
  "description": "Analyses query history for the last N days: tables never queried, most expensive queries, slow repeated queries and cost by table. Returns suggestions only.",
  "parameters": {
    "type": "object",
    "properties": {
      "days": {"type": "integer", "default": 90, "minimum": 7, "maximum": 365},
      "top_n": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20}
    }
  },
  "returns": "JSON: unused_tables, top_queries, top_queries_cost_share, slow_repeated, cost_by_table"
}
```

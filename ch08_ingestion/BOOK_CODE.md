# Chapter 8 — Ingestion: ETL, ELT and real life

## Code from the book

Every code block of this chapter, in book order, under the book's section headings.
Runnable files are in this folder; for scripts printed as "(shortened)" in the book, the full version is the file here.

### 8.3 Pulling data from an API, files and a database

**Code 8.1**

```python
"""ingest_to_bronze.py - moves sources into the bronze layer without changing them (Chapter 8)."""
import argparse, csv, hashlib, json, re, uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
BRONZE = Path("data/layers/bronze")
FILE_LOG = BRONZE / "_ingest_log.parquet"
NOT_LOADED = {"Sheet1.csv", "dim_order.csv"}  # Chapter 7: duplicate table and junk table, never loaded


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_audit(df: pd.DataFrame, source_file: str, batch_id: str) -> pd.DataFrame:
    data_cols = [c for c in df.columns if not c.startswith("_")]
    # The fingerprint uses data columns only; the file name is not part of it.
    df["_row_hash"] = df[data_cols].fillna("").astype(str).agg("\x1f".join, axis=1).map(sha256_text)
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    df["_source_file"] = source_file
    df["_batch_id"] = batch_id
    return df


def read_pos_file(path: Path) -> pd.DataFrame:
    """MM03: ';' delimited, Windows-1252, H (receipt header) and L (receipt line) records in one file."""
    rows = []
    with open(path, encoding="cp1252", newline="") as f:
        for parts in csv.reader(f, delimiter=";"):
            if not parts:
                continue
            row = {"rec_type": parts[0], "raw_line": ";".join(parts)}
            row.update({f"field_{i}": v for i, v in enumerate(parts[1:], start=1)})
            rows.append(row)
    return pd.DataFrame(rows, dtype="string")


def read_csv_as_text(path: Path) -> pd.DataFrame:
    """CSV copies of the Bazaarly dump: no value is interpreted."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_jsonl_as_text(path: Path) -> pd.DataFrame:
    """BZ11 support tickets: one JSON object per line; fields kept as text, the line itself in raw_json."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            rows.append({**{k: str(v) for k, v in obj.items()}, "raw_json": line})
    return pd.DataFrame(rows, dtype="string")


def read_fx(day: str) -> pd.DataFrame:
    from fx_api_mock import get_rates  # OP02: {"date": ..., "rates": {"CAD": ..., ...}}
    payload = get_rates(day)
    return pd.DataFrame(
        [{"date": payload["date"], "currency": cur, "rate_to_usd": str(rate),
          "raw_json": json.dumps(payload)} for cur, rate in payload.get("rates", {}).items()],
        dtype="string",
    )
```

### 8.4 Reliable ingestion: idempotency, backfill, late data, dead-letter queue

**Code 8.2**

```python
def already_loaded(file_hash: str) -> bool:
    return FILE_LOG.exists() and file_hash in set(pd.read_parquet(FILE_LOG)["file_hash"])


def log_file(path: Path, file_hash: str, batch_id: str, status: str, rows: int) -> None:
    entry = pd.DataFrame([{"file_name": path.name, "file_hash": file_hash, "batch_id": batch_id,
                           "status": status, "rows": rows,
                           "logged_at": datetime.now(timezone.utc).isoformat()}])
    log = pd.concat([pd.read_parquet(FILE_LOG), entry]) if FILE_LOG.exists() else entry
    log.to_parquet(FILE_LOG, index=False)


def append_new_rows(table: str, df: pd.DataFrame) -> dict:
    """Appends only rows that have not been seen before (idempotent)."""
    target = BRONZE / f"{table}.parquet"
    df = df.drop_duplicates("_row_hash")
    old = pd.read_parquet(target) if target.exists() else df.iloc[0:0]
    new = df[~df["_row_hash"].isin(set(old["_row_hash"]))]
    pd.concat([old, new], ignore_index=True).to_parquet(target, index=False)
    return {"table": table, "rows_in": len(df), "rows_added": len(new), "rows_skipped": len(df) - len(new)}


def missing_pos_days(since: str, until: str) -> list[str]:
    have = {re.search(r"pos_(\d{8})", p.name).group(1) for p in (RAW / "meridian/pos").glob("pos_*.csv")}
    days = pd.date_range(since, until).strftime("%Y%m%d")
    return [d for d in days if d not in have]


def run(source: str = "mm_pos", since: str = "2025-01-01", until: str = "2027-06-30") -> dict:
    """Called by the agent tool 'yukleme'. Writes to bronze only."""
    batch_id = uuid.uuid4().hex[:12]
    summary = {"batch_id": batch_id, "source": source, "tables": [], "skipped_files": [],
               "dead_letter": [], "missing_days": []}
    if source == "mm_pos":
        lo, hi = since.replace("-", ""), until.replace("-", "")
        for path in sorted((RAW / "meridian/pos").glob("pos_*.csv")):
            day = re.search(r"pos_(\d{8})", path.name).group(1)
            if not lo <= day <= hi:
                continue
            file_hash = sha256_file(path)
            if already_loaded(file_hash):
                summary["skipped_files"].append(path.name)
                continue
            try:
                df = add_audit(read_pos_file(path), path.name, batch_id)
            except (UnicodeDecodeError, csv.Error) as err:
                (RAW / "_dead_letter").mkdir(exist_ok=True)
                path.rename(RAW / "_dead_letter" / path.name)
                summary["dead_letter"].append({"file": path.name, "error": str(err)})
                continue
            summary["tables"].append(append_new_rows("mm_pos_raw", df))
            log_file(path, file_hash, batch_id, "loaded", len(df))
        summary["missing_days"] = missing_pos_days(since, until)
    elif source == "bazaarly_dump":
        for path in sorted((RAW / "bazaarly/csv").glob("*.csv")):
            if path.name in NOT_LOADED:
                summary["skipped_files"].append(path.name)
                continue
            df = add_audit(read_csv_as_text(path), path.name, batch_id)
            summary["tables"].append(append_new_rows(path.stem, df))
        # Since January 2027 Bazaarly orders arrive as daily incremental files (BZ05c)
        for path in sorted((RAW / "bazaarly/bz_orders_2027").glob("*.csv")):
            df = add_audit(read_csv_as_text(path), path.name, batch_id)
            summary["tables"].append(append_new_rows("bz_orders_2027", df))
    elif source == "bz_tickets":
        # BZ11: hourly, cumulative JSON Lines export; _row_hash keeps re-sent tickets out
        path = RAW / "bazaarly/bz_support_tickets.jsonl"
        file_hash = sha256_file(path)
        if already_loaded(file_hash):
            summary["skipped_files"].append(path.name)
        else:
            df = add_audit(read_jsonl_as_text(path), path.name, batch_id)
            summary["tables"].append(append_new_rows("bz_support_tickets", df))
            log_file(path, file_hash, batch_id, "loaded", len(df))
    elif source == "fx":
        for day in pd.date_range(since, until).strftime("%Y-%m-%d"):
            df = read_fx(day)
            if len(df):
                summary["tables"].append(append_new_rows("ref_fx_rates", add_audit(df, f"api:{day}", batch_id)))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="mm_pos", choices=["mm_pos", "bazaarly_dump", "bz_tickets", "fx"])
    p.add_argument("--since", default="2025-01-01")
    p.add_argument("--until", default="2027-06-30")
    p.add_argument("--env", default="local", choices=["local", "databricks"])
    a = p.parse_args()
    print(json.dumps(run(a.source, a.since, a.until), indent=2, ensure_ascii=False))
```

### 8.5 Streaming data: message queues, Kafka, delivery guarantees; start with batch

**Code 8.3**

```python
"""stream_simulator.py - replays BZ09 events as a stream and writes them to bronze in micro-batches (Chapter 8)."""
import json, random, uuid
from pathlib import Path

import pandas as pd

from ingest_to_bronze import add_audit, append_new_rows

EVENTS = Path("data/raw/bazaarly/events")


def produce(seed: int = 2027, jitter: int = 50):
    """Producer: reads events file by file and shuffles their order within small windows."""
    rnd, window = random.Random(seed), []
    for path in sorted(EVENTS.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            window.append((path.name, line))
            if len(window) >= jitter:
                rnd.shuffle(window)
                yield from window
                window = []
    rnd.shuffle(window)
    yield from window


def to_row(source_file: str, line: str) -> dict:
    event = json.loads(line)
    time_field = "event_time" if "event_time" in event else "ts"
    return {"event_id": str(event.get("event_id", "")), "time_field": time_field,
            "time_value": str(event.get(time_field, "")), "raw_json": line, "_file": source_file}


def consume(batch_size: int = 500) -> dict:
    """Consumer: appends events to bronze.bz_events in batches."""
    batch_id, batch, totals = uuid.uuid4().hex[:12], [], {"rows_in": 0, "rows_added": 0, "rows_skipped": 0}

    def flush(rows):
        df = pd.DataFrame(rows, dtype="string")
        files = df.pop("_file")
        df = add_audit(df, ",".join(sorted(set(files))), batch_id)
        result = append_new_rows("bz_events", df)
        for key in totals:
            totals[key] += result[key]

    for source_file, line in produce():
        batch.append(to_row(source_file, line))
        if len(batch) >= batch_size:
            flush(batch)
            batch = []
    if batch:
        flush(batch)
    return {"batch_id": batch_id, "table": "bz_events", **totals}


if __name__ == "__main__":
    print(json.dumps(consume(), indent=2))
```

### 8.6 Ingestion code with AI, and script → the “yukleme” tool

**Code 8.4**

```json
{
  "name": "yukleme",
  "description": "Loads one source into the bronze layer without changing data. Skips duplicate files and rows, reports missing days and unreadable files.",
  "parameters": {
    "type": "object",
    "properties": {
      "source": {"type": "string", "enum": ["mm_pos", "bazaarly_dump", "bz_tickets", "fx"]},
      "since": {"type": "string", "format": "date", "description": "First day to load (inclusive)"},
      "until": {"type": "string", "format": "date", "description": "Last day to load (inclusive)"}
    },
    "required": ["source"]
  }
}
```

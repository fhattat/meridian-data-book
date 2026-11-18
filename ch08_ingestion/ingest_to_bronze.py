"""ingest_to_bronze.py - moves sources into the bronze layer without changing them (Chapter 8).

Book version: Chapter 8.3-8.4. Repo additions (marked "repo:"): the "meridian_files", "bz_events",
"bz_payments", "bz_returns" and "all" sources, --size for run_pipeline.py, one write per table per run
(faster than one write per file) and the backfill of late files from meridian/pos_late/.
"""
import argparse, csv, hashlib, json, re, shutil, uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))   # repo: fx_api_mock / stream_simulator next to this file

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
    from fx_api_mock import get_rates  # noqa: E402  # OP02: {"date": ..., "rates": {"CAD": ..., ...}}
    payload = get_rates(day)
    return pd.DataFrame(
        [{"date": payload["date"], "currency": cur, "rate_to_usd": str(rate),
          "raw_json": json.dumps(payload)} for cur, rate in payload.get("rates", {}).items()],
        dtype="string",
    )


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


def backfill_late_files(missing: list[str]) -> list[Path]:
    """repo: Chapter 8.4 backfill. A missing day's file that landed in the wrong folder (pos_late/)
    is found and loaded for that day only. data/raw is never modified: the file is read where it is."""
    found = []
    for day in missing:
        late = RAW / "meridian/pos_late" / f"pos_{day}.csv"
        if late.exists():
            found.append(late)
    return found


def load_pos(summary: dict, batch_id: str, since: str, until: str, seen: set,
             paths: list[Path] | None = None) -> None:
    lo, hi = since.replace("-", ""), until.replace("-", "")
    frames, logs = [], []
    for path in paths if paths is not None else sorted((RAW / "meridian/pos").glob("pos_*.csv")):
        day = re.search(r"pos_(\d{8})", path.name).group(1)
        if not lo <= day <= hi:
            continue
        file_hash = sha256_file(path)
        if file_hash in seen or already_loaded(file_hash):
            summary["skipped_files"].append(path.name)
            continue
        try:
            df = add_audit(read_pos_file(path), path.name, batch_id)
        except (UnicodeDecodeError, csv.Error) as err:
            (RAW / "_dead_letter").mkdir(exist_ok=True)
            path.rename(RAW / "_dead_letter" / path.name)
            summary["dead_letter"].append({"file": path.name, "error": str(err)})
            continue
        seen.add(file_hash)
        frames.append(df)
        logs.append((path, file_hash, len(df)))
    if frames:                                   # repo: one write per run instead of one per file
        summary["tables"].append(append_new_rows("mm_pos_raw", pd.concat(frames, ignore_index=True)))
    for path, file_hash, n in logs:
        log_file(path, file_hash, batch_id, "loaded", n)


def loaded_days() -> set[str]:
    """Days whose POS file is in the ingest log (also files loaded from pos_late/)."""
    if not FILE_LOG.exists():
        return set()
    names = pd.read_parquet(FILE_LOG)["file_name"]
    return {m.group(1) for m in names.map(lambda n: re.search(r"pos_(\d{8})", str(n))) if m}


MERIDIAN_FILES = ["mm_stores.csv", "mm_regions.csv", "mm_products.csv", "mm_vendors.csv",
                  "mm_inventory_monthly.xlsx", "mm_loyalty_members.csv", "mm_campaign_log.csv",
                  "mm_campaign_products.csv", "mm_sales_targets.csv", "mm_hr_employees.csv",
                  "mm_finance_accounts.csv"]


def read_excel_as_text(path: Path) -> pd.DataFrame:
    """MM05: the inventory workbook; every cell as text (the header row inside the data stays)."""
    df = pd.read_excel(path, dtype=str).fillna("")
    df.columns = [str(c) for c in df.columns]
    return df


def run(source: str = "mm_pos", since: str = "2025-01-01", until: str = "2027-06-30") -> dict:
    """Called by the agent tool 'yukleme'. Writes to bronze only."""
    BRONZE.mkdir(parents=True, exist_ok=True)
    batch_id = uuid.uuid4().hex[:12]
    summary = {"batch_id": batch_id, "source": source, "tables": [], "skipped_files": [],
               "dead_letter": [], "missing_days": []}
    sources = (["mm_pos", "meridian_files", "bazaarly_dump", "bz_tickets", "bz_events", "bz_payments", "fx"]
               if source == "all" else [source])
    seen: set = set()
    for src in sources:
        if src == "mm_pos":
            load_pos(summary, batch_id, since, until, seen)
            missing = [d for d in missing_pos_days(since, until) if d not in loaded_days()]
            if source == "all":                  # repo: nightly run does what Deniz did by hand in 8.4
                for path in backfill_late_files(missing):
                    day = re.search(r"pos_(\d{8})", path.name).group(1)
                    d = f"{day[:4]}-{day[4:6]}-{day[6:]}"
                    load_pos(summary, batch_id, d, d, seen, paths=[path])
                    summary.setdefault("backfilled_days", []).append(day)
                missing = [d for d in missing if d not in loaded_days()]
            summary["missing_days"] = missing
        elif src == "meridian_files":            # repo: MM01, MM02, MM04-MM11
            for name in MERIDIAN_FILES:
                path = RAW / "meridian" / name
                if not path.exists():
                    continue
                df = read_excel_as_text(path) if path.suffix == ".xlsx" else read_csv_as_text(path)
                summary["tables"].append(append_new_rows(path.stem, add_audit(df, path.name, batch_id)))
        elif src == "bazaarly_dump":
            for path in sorted((RAW / "bazaarly/csv").glob("*.csv")):
                if path.name in NOT_LOADED:
                    summary["skipped_files"].append(path.name)
                    continue
                df = add_audit(read_csv_as_text(path), path.name, batch_id)
                summary["tables"].append(append_new_rows(path.stem, df))
            # Since January 2027 Bazaarly orders arrive as daily incremental files (BZ05c)
            daily = [add_audit(read_csv_as_text(p), p.name, batch_id)
                     for p in sorted((RAW / "bazaarly/bz_orders_2027").glob("*.csv"))]
            if daily:                            # columns may differ per day (status_code -> status)
                summary["tables"].append(append_new_rows("bz_orders_2027", pd.concat(daily, ignore_index=True)))
        elif src == "bz_tickets":
            # BZ11: hourly, cumulative JSON Lines export; _row_hash keeps re-sent tickets out
            path = RAW / "bazaarly/bz_support_tickets.jsonl"
            file_hash = sha256_file(path)
            if already_loaded(file_hash):
                summary["skipped_files"].append(path.name)
            else:
                df = add_audit(read_jsonl_as_text(path), path.name, batch_id)
                summary["tables"].append(append_new_rows("bz_support_tickets", df))
                log_file(path, file_hash, batch_id, "loaded", len(df))
        elif src == "bz_events":                 # repo: the whole BZ09 folder in one batch;
            from stream_simulator import EVENTS, to_row   # stream_simulator.py replays it as a stream
            rows = [{**to_row(p.name, line)} for p in sorted(EVENTS.glob("*.jsonl"))
                    for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
            df = pd.DataFrame(rows, dtype="string")
            files = df.pop("_file")
            df = add_audit(df, "events/*.jsonl", batch_id)
            df["_source_file"] = files.to_numpy()
            summary["tables"].append(append_new_rows("bz_events", df))
        elif src == "bz_payments":               # repo: BZ10 (Parquet; CSV if pyarrow was missing)
            base = RAW / "bazaarly/bz_payment_transactions"
            path = base.with_suffix(".parquet") if base.with_suffix(".parquet").exists() else base.with_suffix(".csv")
            df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, dtype=str)
            df = df.astype(str)
            summary["tables"].append(append_new_rows("bz_payment_transactions", add_audit(df, path.name, batch_id)))
        elif src == "bz_returns":                # repo: BZ13, connected in July 2027 (Chapter 16)
            path = RAW / "bazaarly/bz_returns.csv"
            summary["tables"].append(append_new_rows("bz_returns", add_audit(read_csv_as_text(path), path.name, batch_id)))
        elif src == "fx":
            frames = [read_fx(day) for day in pd.date_range(since, until).strftime("%Y-%m-%d")]
            frames = [add_audit(df, f"api:{df['date'].iloc[0]}", batch_id) for df in frames if len(df)]
            if frames:                           # repo: one write for all days
                summary["tables"].append(append_new_rows("ref_fx_rates", pd.concat(frames, ignore_index=True)))
    return summary


SOURCES = ["mm_pos", "meridian_files", "bazaarly_dump", "bz_tickets", "bz_events", "bz_payments",
           "bz_returns", "fx", "all"]

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="all", choices=SOURCES)
    p.add_argument("--since", default="2025-01-01")
    p.add_argument("--until", default="2027-06-30")
    p.add_argument("--env", default="local", choices=["local", "databricks"])
    p.add_argument("--size", default="small", choices=["small", "large"])   # repo: passed by run_pipeline.py
    a = p.parse_args()
    if a.env != "local":
        raise SystemExit("On Databricks run this file in a notebook/job and write Delta tables (Chapter 8.3).")
    print(json.dumps(run(a.source, a.since, a.until), indent=2, ensure_ascii=False))

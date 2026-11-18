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

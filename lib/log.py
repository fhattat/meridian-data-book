"""lib/log.py - one log format for every script (Chapter 13.4).

Lines look like the OP05 pipeline logs, so check_pipeline_logs.py can read our own runs too:
2027-04-16T06:10:12Z INFO  step=ingest source=ref_fx_rates msg="done rows=402" attempt=1
Never put personal data (e-mail, phone, names) in a message.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(os.environ.get("MERIDIAN_LOG_DIR", "reports/logs"))


def log(step: str, msg: str, level: str = "INFO", source: str | None = None, attempt: int = 1) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    src = f" source={source}" if source else ""
    line = f'{ts} {level:<5} step={step}{src} msg="{msg}" attempt={attempt}'
    print(line, file=sys.stderr)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / f"{ts[:10]}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line

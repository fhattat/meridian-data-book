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
    p.add_argument("--no-append", action="store_true", help="repo: do not add an open record to incident_log.yaml")
    a = p.parse_args()
    print(json.dumps(run(a.log_path, append=not a.no_append), indent=2))

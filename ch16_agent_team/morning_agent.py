"""morning_agent.py - runs every morning at 07:00 America/New_York.

Task: check the nightly job, classify findings by the runbook,
produce DRAFTS of a report and of one note per domain.
Never: delete, re-run, publish to production, send email.
"""
import json
from datetime import date, timedelta
from pathlib import Path

from lib.llm import ask_json          # thin wrapper over ask_llm() from Chapter 15
from lib.io import read_sql           # read-only query
from mcp_server import incident, quality  # the tools from 16.2

RUNBOOK = Path("runbooks/morning_check.md").read_text()
MAX_TURNS = 3
FORBIDDEN = ("rerun", "re-run", "delete", "drop table", "deploy",
             "publish to production", "send email")
RECIPIENTS = {"store_pos": "marcus", "marketplace": "bazaarly_source_owner",
              "customer": "priya", "events": "sam", "summary": "deniz"}
EXTRA_CHECKS = {
    "channel_breakdown": """
        SELECT source_company, channel_code, COUNT(*) AS orders
        FROM silver.bz_orders WHERE order_local_date = ?
        GROUP BY ALL ORDER BY orders DESC""",
    "incident_lookup": None,         # calls the incident tool
    "late_step": """
        SELECT step, MAX(ts) AS finished_at FROM ops.pipeline_log
        WHERE run_date = ? GROUP BY step ORDER BY finished_at DESC LIMIT 3""",
}


def fixed_checks(day: date) -> list[dict]:
    """Workflow part: threshold checks are done by rules; the model stays out."""
    findings = []
    for r in quality()["problems"]:                  # also updates quality.check_results
        findings.append({"check": r["check"], "domain": "summary",
                         "level": "critical" if r["status"] == "fail" else "warning",
                         "observed": r["observed"], "expected": r["expected"]})
    vol = read_sql("""
        SELECT COUNT(*) FILTER (WHERE order_local_date = ?) AS today,
               COUNT(*) FILTER (WHERE order_local_date = ?) AS last_week
        FROM silver.bz_orders""", [day, day - timedelta(days=7)]).iloc[0]
    change = (vol.today - vol.last_week) / max(vol.last_week, 1)
    if change <= -0.10 or vol.today == 0:
        findings.append({"check": "bz_orders_volume", "domain": "marketplace",
                         "level": "critical" if change <= -0.20 or vol.today == 0 else "warning",
                         "observed": int(vol.today), "expected": int(vol.last_week),
                         "change_pct": round(change * 100, 1)})
    return findings


def run_extra(name: str, day: date) -> dict:
    if name not in EXTRA_CHECKS:                    # requests outside the runbook are refused
        return {"error": f"check not allowed: {name}"}
    if name == "incident_lookup":
        return incident(log_date=day.isoformat())
    return {"rows": read_sql(EXTRA_CHECKS[name], [day]).to_dict("records")}


def accept(report: dict) -> list[str]:
    """Loop engineering: the report is checked against the acceptance criteria before it goes to a human."""
    problems = []
    for f in report.get("findings", []):
        if f.get("level") == "critical" and not f.get("evidence_query"):
            problems.append(f"{f.get('check')}: no evidence query")
    for r in report.get("recommendations", []):
        if not r.get("based_on"):
            problems.append(f"recommendation without basis: {r.get('text', '')[:50]}")
        if any(w in r.get("text", "").lower() for w in FORBIDDEN):
            problems.append(f"forbidden action recommended: {r.get('text', '')[:50]}")
    return problems


def run(day: str | None = None) -> dict:
    day = date.fromisoformat(day) if day else date.today() - timedelta(days=1)
    findings, evidence = fixed_checks(day), []
    for _ in range(MAX_TURNS):                      # small ReAct loop
        reply = ask_json(system=RUNBOOK, prompt=json.dumps(
            {"day": str(day), "findings": findings, "evidence": evidence}) +
            '\nIf needed, pick one extra check, or say "done": {"next": ...}')
        if reply.get("next") in (None, "done"):
            break
        evidence.append({"check": reply["next"], "result": run_extra(reply["next"], day)})

    problems = []
    for attempt in (1, 2):                          # acceptance loop: at most two attempts
        report = ask_json(system=RUNBOOK, prompt=json.dumps(
            {"day": str(day), "findings": findings, "evidence": evidence,
             "previous_problems": problems}) +
            '\nWrite it by the runbook: {"findings": [...], "recommendations": '
            '[{"text": ..., "based_on": ...}], "html": ..., "drafts": {"<domain>": ...}}')
        problems = accept(report)
        if not problems:
            break
    if problems:                                    # failed twice: leave it to a human
        report["html"] = ("<p><b>I'm not sure.</b> Acceptance criteria not met: "
                          + "; ".join(problems) + "</p>" + report.get("html", ""))

    out = Path("reports"); (out / "drafts").mkdir(parents=True, exist_ok=True)
    (out / f"morning_{day}.html").write_text(report.get("html", ""))
    for domain, text in report.get("drafts", {}).items():
        if domain in RECIPIENTS:
            (out / "drafts" / f"{RECIPIENTS[domain]}_{day}.md").write_text(text)
    return {"day": str(day), "findings": findings, "extra_checks": [e["check"] for e in evidence],
            "accepted": not problems, "sent": False}   # nothing was sent


if __name__ == "__main__":                       # repo: command line entry
    import sys
    try:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--env", default="local", choices=["local", "databricks"])
        ap.add_argument("--day", help="YYYY-MM-DD; Chapter 16.3 replays 2027-04-15")
        print(json.dumps(run(ap.parse_args().day), indent=2, ensure_ascii=False, default=str))
    except NotImplementedError as exc:
        sys.exit(f"{exc}. Connect ask_llm() in lib/llm.py (or set MERIDIAN_LLM=anthropic), then run again.")

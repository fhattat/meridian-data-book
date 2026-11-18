"""orchestrator_agent.py - manager agent: hands out work, asks a human when needed."""
import json
import uuid
from pathlib import Path

from lib.llm import ask_json
from mcp_server import profil, yukleme, temizlik, kalite, katalog, ariza

PLAYBOOKS = {
    "new_source": ["profil", "approve:contract", "yukleme", "temizlik", "kalite", "katalog",
                   "approve:publish"],
    "health_check": ["kalite", "ariza"],
    "metadata_refresh": ["katalog"],
}
SUB_AGENTS = {"profil": profil, "yukleme": yukleme, "temizlik": temizlik,
              "kalite": kalite, "katalog": katalog, "ariza": ariza}
APPROVALS = Path("reports/approvals")
AGENT_NAME = "pipeline_agent"      # Chapter 17: at most 30 steps, 200,000 tokens
MAX_STEPS = 30


def plan(goal: str) -> dict:
    """The model only picks a playbook and proposes parameters; it cannot invent steps."""
    reply = ask_json(prompt=json.dumps({"goal": goal, "playbooks": list(PLAYBOOKS)}) +
                     '\nJSON: {"playbook": ..., "params": {...}, "why": ...}')
    if reply["playbook"] not in PLAYBOOKS:
        raise ValueError(f"unknown playbook: {reply['playbook']}")
    return reply


def ask_human(run_id: str, step: str, context: dict) -> None:
    APPROVALS.mkdir(parents=True, exist_ok=True)
    (APPROVALS / f"pending_{run_id}.json").write_text(
        json.dumps({"run_id": run_id, "waiting_for": step, "context": context}, indent=2))


def run(goal: str, resume_from: int = 0, run_id: str | None = None) -> dict:
    p = plan(goal)
    run_id = run_id or uuid.uuid4().hex[:8]
    steps, log = PLAYBOOKS[p["playbook"]], []
    for i, step in enumerate(steps[resume_from:], start=resume_from):
        if i >= MAX_STEPS:                              # step limit: stop, ask a human
            ask_human(run_id, "review:step_limit", {"log": log})
            return {"run_id": run_id, "status": "waiting_for_human", "log": log}
        if step.startswith("approve:"):
            ask_human(run_id, step, {"goal": goal, "log": log})
            return {"run_id": run_id, "status": "waiting_for_human", "step": step,
                    "resume_from": i + 1, "log": log}
        result = SUB_AGENTS[step](**p["params"].get(step, {}))
        log.append({"step": step, "summary": {k: result.get(k) for k in ("status", "rows")}})
        if needs_human(step, result):
            ask_human(run_id, f"review:{step}", {"result": result, "log": log})
            return {"run_id": run_id, "status": "waiting_for_human", "step": step,
                    "resume_from": i + 1, "log": log}
    return {"run_id": run_id, "status": "done", "log": log}


def needs_human(step: str, result: dict) -> bool:
    """The table below, as code. The rules live here, not in the model."""
    if result.get("status") in ("fail", "hold"):
        return True
    if step == "profil" and (result.get("pii_columns") or result.get("open_questions")):
        return True
    if step == "kalite" and not result.get("publish_allowed", True):   # a critical rule failed
        return True
    return False


if __name__ == "__main__":                       # repo: command line entry
    import sys
    try:
        print(json.dumps(run(sys.argv[1] if len(sys.argv) > 1 else "Bring the bz_returns source onto the platform"), indent=2, ensure_ascii=False, default=str))
    except NotImplementedError as exc:
        sys.exit(f"{exc}. Connect ask_llm() in lib/llm.py (or set MERIDIAN_LLM=anthropic), then run again.")

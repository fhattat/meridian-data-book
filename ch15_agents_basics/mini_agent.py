"""mini_agent.py - the smallest ReAct agent, with two tools (Chapter 15).

Tools: profile (Chapter 7, profile_source.run) and row_count (row count in DuckDB).
The model call sits behind ask_llm(); connect it to your own assistant.
"""
import json, logging, re, sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "ch07_profiling"))
from profile_source import run as profile_run  # noqa: E402

DB = ROOT / "data" / "meridian.duckdb"
MAX_STEPS = 6
(ROOT / "reports").mkdir(exist_ok=True)
logging.basicConfig(filename=ROOT / "reports" / "mini_agent.log", level=logging.INFO,
                    format="%(asctime)s %(message)s")

TOOLS = {
    "profile": {
        "description": "Profiles a source file before ingestion. Read-only.",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string", "description": "Source file path"}},
                       "required": ["path"]}},
    "row_count": {
        "description": "Returns the row count of a bronze, silver or gold table, optionally for one load date. Read-only.",
        "parameters": {"type": "object",
                       "properties": {"table": {"type": "string", "description": "schema.table"},
                                      "load_date": {"type": "string", "description": "YYYY-MM-DD, bronze only"}},
                       "required": ["table"]}},
}

SYSTEM = """You are the data quality assistant of Meridian Market.
Use only the listed tools. Reply with JSON only, in one of two forms:
{"thought": "...", "action": "<tool name>", "args": {...}}
{"thought": "...", "final": "<short report>"}
Every number in the final report must come from a tool result.
If you are not sure, finish with 'final' and say what a human should check."""


def row_count(table, load_date=None):
    if not re.fullmatch(r"(bronze|silver|gold)\.[a-z0-9_]+", table):
        return {"error": "table not allowed"}
    con = duckdb.connect(str(DB), read_only=True)
    sql, params = f"SELECT COUNT(*) FROM {table}", []
    if load_date:
        sql += " WHERE CAST(_ingested_at AS DATE) = ?"
        params.append(load_date)
    return {"table": table, "load_date": load_date, "rows": con.execute(sql, params).fetchone()[0]}


def call_tool(name, args):
    if name == "profile":
        s = profile_run(**args)
        keep = ("table", "rows", "empty_columns", "pii_columns", "twin_name_suspects", "open_questions")
        return {k: s[k] for k in keep}        # context engineering: a summary, not the whole report
    if name == "row_count":
        return row_count(**args)
    return {"error": f"unknown tool {name}"}


def ask_llm(messages, tools):
    """Adapter layer: call your assistant's API here and return the model's JSON reply as text."""
    raise NotImplementedError("connect ask_llm to your own assistant")


def run(task, ask=ask_llm, max_steps=MAX_STEPS):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    for step in range(1, max_steps + 1):
        try:
            reply = json.loads(ask(messages, TOOLS))                    # think
        except json.JSONDecodeError:
            return {"status": "stopped", "steps": step, "reason": "model reply is not JSON"}
        logging.info("step=%d reply=%s", step, json.dumps(reply, ensure_ascii=False))
        if "final" in reply:
            return {"status": "done", "steps": step, "report": reply["final"]}
        if reply.get("action") not in TOOLS:
            return {"status": "stopped", "steps": step, "reason": "unknown or missing action"}
        result = call_tool(reply["action"], reply.get("args", {}))     # act
        logging.info("step=%d tool=%s result=%s", step, reply["action"],
                     json.dumps(result, ensure_ascii=False, default=str))
        messages.append({"role": "assistant", "content": json.dumps(reply)})
        messages.append({"role": "user", "content": "Observation: " + json.dumps(result, default=str)})  # observe
    return {"status": "stopped", "steps": max_steps, "reason": "max steps reached; ask a human"}


class ScriptedLLM:
    """A fake model for testing the loop logic without an API key."""
    def __init__(self, replies):
        self.replies = iter(replies)

    def __call__(self, messages, tools):
        return json.dumps(next(self.replies))


if __name__ == "__main__":
    fake = ScriptedLLM([
        {"thought": "Let me count yesterday's POS load.", "action": "row_count",
         "args": {"table": "bronze.mm_pos_raw", "load_date": "2027-07-12"}},
        {"thought": "The count is lower than expected; let me profile the source file.", "action": "profile",
         "args": {"path": "data/raw/meridian/pos/pos_20270712.csv"}},
        {"thought": "I have the evidence.", "final": "POS load checked; details are in the log."},
    ])
    print(json.dumps(run("Was yesterday's POS load normal?", ask=fake), indent=2, ensure_ascii=False))

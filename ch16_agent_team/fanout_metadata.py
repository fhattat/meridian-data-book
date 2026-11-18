"""fanout_metadata.py - builds metadata with one sub-agent per source."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

from lib.llm import ask_json
from mcp_server import catalog

GROUPS = yaml.safe_load(open("governance/source_groups.yaml"))   # the table above
MAX_WORKERS = 4                    # at most four sub-agents at once (Chapter 17 limit: 6)
TOKEN_BUDGET = 200_000             # pipeline_agent's budget; a cap for the whole run

SUB_AGENT_RULES = """You look only at the metadata of the source you were given.
You may draft empty descriptions; mark every draft as description_source: ai_draft.
Do not invent a meaning that is not in the source document; if unsure, leave it empty.
Never change the technical fields (type, null rate, distinct count)."""


def sub_agent(group: str, tables: list[str], guide_text: str) -> dict:
    meta = catalog(tables=tables)                       # rule-based metadata first
    empty = [c for t in meta["tables"]                  # column details live in the YAML under metadata/
             for c in yaml.safe_load(open(f"metadata/{t['table']}.yaml"))["columns"]
             if not c["description"]]
    if not empty:
        return {"group": group, "drafts": [], "tokens": 0}
    prompt = json.dumps({"source_doc": guide_text, "columns": empty})
    reply = ask_json(system=SUB_AGENT_RULES, prompt=prompt)
    tokens = (len(SUB_AGENT_RULES) + len(prompt) + len(json.dumps(reply))) // 4  # rough estimate
    return {"group": group, "drafts": reply["drafts"], "tokens": tokens}


def run() -> dict:
    results, used = [], 0
    with ThreadPoolExecutor(MAX_WORKERS) as pool:
        futures = [pool.submit(sub_agent, g, spec["tables"], open(spec["doc"]).read())
                   for g, spec in GROUPS.items()]
        for f in as_completed(futures):
            r = f.result()
            used += r["tokens"]
            results.append(r)
            if used > TOKEN_BUDGET:
                pool.shutdown(cancel_futures=True)      # budget exceeded: stop and report
                break
    conflicts = find_conflicts(results)                 # manager: two different drafts for the same column
    write_drafts(results)                               # metadata/<schema>.<table>.yaml, ai_draft
    return {"groups": len(results), "drafts": sum(len(r["drafts"]) for r in results),
            "conflicts": conflicts, "tokens_used": used, "approved": 0}


def write_drafts(results: list[dict]) -> None:
    """repo: drafts never overwrite reviewed text. They go to reports/drafts/ for the steward and,
    for a column whose description is empty, into metadata/<schema>.<table>.yaml as ai_draft."""
    out = Path("reports/drafts"); out.mkdir(parents=True, exist_ok=True)
    for r in results:
        (out / f"metadata_{r['group']}.yaml").write_text(
            yaml.safe_dump(r["drafts"], allow_unicode=True, sort_keys=False), encoding="utf-8")
        for d in r["drafts"]:
            f = Path("metadata") / f"{d.get('table', '')}.yaml"
            if not d.get("table") or not f.exists():
                continue
            meta = yaml.safe_load(f.read_text(encoding="utf-8"))
            for c in meta["columns"]:
                if c["name"] == d["column_name"] and not c.get("description"):
                    c["description"], c["description_source"] = d["description"], "ai_draft"
            f.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")


def find_conflicts(results: list[dict]) -> list[dict]:
    seen, out = {}, []
    for r in results:
        for d in r["drafts"]:
            key = d["column_name"]                          # same name, different table
            if key in seen and seen[key]["text"] != d["description"]:
                out.append({"column": key, "a": seen[key], "b": d})
            seen.setdefault(key, {"group": r["group"], "text": d["description"]})
    return out


if __name__ == "__main__":                       # repo: command line entry
    import sys
    try:
        print(json.dumps(run(), indent=2, ensure_ascii=False, default=str))
    except NotImplementedError as exc:
        sys.exit(f"{exc}. Connect ask_llm() in lib/llm.py (or set MERIDIAN_LLM=anthropic), then run again.")

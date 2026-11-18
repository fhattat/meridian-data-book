"""The agent tool names are the same everywhere: MCP server, guardrails, orchestrator, tool JSON files,
evaluation scenarios and runbooks (Chapters 7-17)."""
import ast
import json
import re
from pathlib import Path

import yaml

TOOLS = {"profile", "ingest", "clean", "quality", "modeling", "incident", "catalog", "review", "search_docs"}
OLD = re.compile(r"\b(profil|yukleme|temizlik|kalite|modelleme|ariza|katalog|inceleme|belge_ara)\b")


def mcp_tools():
    tree = ast.parse(Path("ch16_agent_team/mcp_server.py").read_text(encoding="utf-8"))
    return {f.name for f in tree.body if isinstance(f, ast.FunctionDef)
            and any(getattr(getattr(d, "func", None), "attr", None) == "tool" for d in f.decorator_list)}


def test_mcp_server_exposes_the_seven_core_tools():
    assert mcp_tools() == {"profile", "ingest", "clean", "quality", "modeling", "incident", "catalog"}


def test_write_scope_and_guardrails_use_the_same_names():
    src = Path("ch16_agent_team/mcp_server.py").read_text(encoding="utf-8")
    scope = ast.literal_eval(re.search(r"WRITE_SCOPE = (\{.*?\n\})", src, re.S).group(1))
    assert set(scope) == mcp_tools()
    g = Path("ch17_agent_safety/guardrails.py").read_text(encoding="utf-8")
    policy = ast.literal_eval(re.search(r"POLICY = (\{.*?\n\})", g, re.S).group(1))
    assert policy["pipeline_agent"]["allowed"] <= TOOLS
    assert policy["support_assistant"]["allowed"] == {"search_docs"}


def test_tool_definition_files():
    names = {json.loads(p.read_text(encoding="utf-8"))["name"] for p in Path(".").glob("ch*/tool_*.json")}
    assert names == TOOLS


def test_scenarios_and_playbook_use_known_tools():
    for s in yaml.safe_load(Path("ch17_agent_safety/eval/scenarios.yaml").read_text(encoding="utf-8")):
        for t in s.get("expect_tools", []) + [x for x in s.get("forbid_tools", []) if x != "*"]:
            assert t in TOOLS, (s["id"], t)
    steps = yaml.safe_load(Path("prompts/E17_new_source_playbook.yaml").read_text(encoding="utf-8"))["steps"]
    assert {s for s in steps if not s.startswith("approve:")} <= TOOLS


def test_no_old_turkish_tool_names_left():
    skip = {"raw", ".git"}
    hits = []
    for p in Path(".").rglob("*"):
        if p.is_file() and not skip & set(p.parts) and p.name != "test_tool_names.py" and p.suffix in {".py", ".md", ".yaml", ".yml", ".json", ".txt", ".sql"}:
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if OLD.search(line):
                    hits.append(f"{p}:{n}: {line.strip()[:80]}")
    assert not hits, hits[:10]

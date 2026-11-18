# Bölüm 16 — Script’ten agent ekibine

## Code from the book

Every code block of this chapter, in book order, under the book's section headings (Turkish, as printed).
Runnable files are in this folder; for scripts printed as "(shortened)" the full version is the file here.
Bu dosya bölümdeki bütün kod bloklarını kitaptaki sırasıyla ve alt bölüm başlıklarıyla verir.

### 16.2 Script’leri araç yapmak: mcp_server.py ve yetkiler

> Sunucu. Aşağıdaki iskelet MCP’nin Python SDK’sıyla yazıldı. Her araç iki satır: ilgili script’in run() fonksiyonunu çağırır ve sonucu döner. Aslı iş guarded() sarmalayıcısında.

**Code 16.1**

```python
"""mcp_server.py - exposes Meridian's seven core tools over MCP.

Rule: the server decides permissions, not the model. Each tool may write only
to its own layer; the rule is enforced inside write_table() in lib/io.py.
"""
import os
from contextlib import contextmanager

from mcp.server.fastmcp import FastMCP   # official MCP Python SDK: pip install mcp

import ch07_profiling.profile_source as profile_source
import ch08_ingestion.ingest_to_bronze as ingest_to_bronze
import ch09_medallion.clean_silver as clean_silver
import ch10_quality.quality_checks as quality_checks
import ch11_modeling.model_checks as model_checks
import ch13_operations.check_pipeline_logs as check_pipeline_logs
import ch14_governance.extract_metadata as extract_metadata

WRITE_SCOPE = {            # tool name -> where it may write
    "profil":    ["reports/", "contracts/"],
    "yukleme":   ["bronze"],
    "temizlik":  ["silver"],
    "kalite":    ["quality"],
    "modelleme": [],
    "ariza":     ["ch13_operations/incident_log.yaml"],
    "katalog":   ["metadata/"],
}

mcp = FastMCP("meridian-tools")


@contextmanager
def guarded(tool):
    """Puts the tool's write scope into an environment variable while it runs."""
    os.environ["MERIDIAN_WRITE_SCOPE"] = ",".join(WRITE_SCOPE[tool])
    os.environ["MERIDIAN_TOOL"] = tool
    try:
        yield
    finally:
        os.environ.pop("MERIDIAN_WRITE_SCOPE", None)
        os.environ.pop("MERIDIAN_TOOL", None)


@mcp.tool()
def profil(path: str, table: str = "", guide: str = "ref/source_guide.yaml") -> dict:
    """Profiles a source file before ingestion. Read-only."""
    with guarded("profil"):
        return profile_source.run(path, table or None, guide)


@mcp.tool()
def yukleme(source: str, since: str = "", until: str = "") -> dict:
    """Loads one source into bronze (source: mm_pos | bazaarly_dump | bz_tickets | fx). Writes only to bronze."""
    dates = {k: v for k, v in {"since": since, "until": until}.items() if v}
    with guarded("yukleme"):
        return ingest_to_bronze.run(source=source, **dates)


@mcp.tool()
def temizlik(size: str = "small") -> dict:
    """Rebuilds silver tables from bronze (size: small | large). Writes only to silver."""
    with guarded("temizlik"):
        return clean_silver.run(size=size)


@mcp.tool()
def kalite(rules: str = "ch10_quality/rules.yaml") -> dict:
    """Runs data quality rules. Writes only to the quality schema."""
    with guarded("kalite"):
        return quality_checks.run(rules_path=rules)


@mcp.tool()
def modelleme() -> dict:
    """Tests grain, keys and cardinality of the gold model. Read-only."""
    with guarded("modelleme"):
        return model_checks.run()


@mcp.tool()
def ariza(log_date: str) -> dict:
    """Scans pipeline logs for a date (YYYY-MM-DD) and drafts an incident. Appends to incident log only."""
    with guarded("ariza"):
        return check_pipeline_logs.run(f"data/raw/ops/pipeline_logs/{log_date}.log")


@mcp.tool()
def katalog(tables: list[str]) -> dict:
    """Extracts metadata for tables. Writes only under metadata/."""
    with guarded("katalog"):
        return extract_metadata.run(tables=tables)


if __name__ == "__main__":
    mcp.run()
```

> Sunucudaki WRITE_SCOPE tek başına bir şey korumaz; bir etikettir. Korumayı yapan, script’lerin yazarken kullandığı ortak kapı: lib/io.py’deki write_table(). Önceki bölümlerin kısaltılmış kodlarında bazı script’ler doğrudan to_parquet ya da con.execute ile…

**Code 16.2**

```python
# inside lib/io.py
def _check_scope(target: str) -> None:
    scope = os.environ.get("MERIDIAN_WRITE_SCOPE")
    if scope is None:            # outside a tool (Deniz runs it by hand): no limit
        return
    if not any(target.startswith(s) for s in scope.split(",") if s):
        raise PermissionError(f"{os.environ['MERIDIAN_TOOL']} -> {target}: write outside scope")

def write_table(df, target: str, **kw):
    _check_scope(target)         # e.g. target = "silver.pos_lines"
    ...
```

> Fonksiyon çağırma alternatifi. MCP kullanmayan bir uygulamada aynı araçlar bir sözlük ve bir dağıtıcıyla sunulur:

**Code 16.3**

```python
TOOLS = {"kalite": kalite, "ariza": ariza, "katalog": katalog}   # the functions above

def call_tool(name: str, args: dict) -> dict:
    if name not in TOOLS:
        return {"error": f"unknown tool: {name}"}
    return TOOLS[name](**args)
```

### 16.3 İlk agent: sabah 07:00 pipeline kontrol agent’ı

> Runbook (skill). Bölüm 15.2’de runbooks/morning_check.md dosyasının ilk halini altı adımla yazmıştık; altıncı adım dört yasak eylemi sayıyordu: yeniden çalıştırma, silme, üretime alma, e-posta gönderme. Agent’ı kurarken o dosyayı yeniden tanımlamıyoruz;…

**Code 16.4**

```markdown
# runbooks/morning_check.md (added below the 6 steps from Chapter 15.2)

## Thresholds
| Check                            | Info               | Warning            | Critical                     |
|----------------------------------|--------------------|--------------------|------------------------------|
| Row count (vs. the same weekday last week; replaces "yesterday" in step 2) | within +/- 10% | 10-20% drop | more than 20% drop, or zero |
| Quality rules                    | all pass           | any warning        | critical fail                |
| Freshness (gold last updated)    | before 06:00       | 06:00-07:30        | after 07:30 (SLO breach)     |
| schema_gate                      | pass               | pass_with_warning  | hold                         |
| Log errors                       | timeout fixed on retry | repeated warning | step ending in ERROR       |

## Extra check options (these only)
- channel_breakdown: on a volume drop, break down by channel and source company
- incident_lookup: on a critical log error, run the ariza tool with that day's date
- late_step: on a freshness breach, find in the log which step finished late

## Acceptance criteria (before the report goes to a human)
- Every critical finding has an evidence query (evidence_query).
- Every recommendation names the rule or record it is based on (based_on: rule name or INC- id).
- No recommendation contains any of the four actions in step 6.
- If it fails twice, the report is left to a human with an "I'm not sure" note.

## Recipients (drafts go under reports/drafts/, none are sent)
| Domain        | Sub-agent    | Draft recipient            |
|---------------|--------------|----------------------------|
| Store / POS   | store_pos    | Marcus                     |
| Marketplace   | marketplace  | Bazaarly source owner      |
| Customer      | customer     | Priya                      |
| Events        | events       | Sam                        |
| Summary       | Bit (manager) | Deniz                     |
- For every critical finding that affects the dashboard, a separate short note to Marcus (he owns the dashboard).
```

> Kod. Önce bir hazırlık: Bölüm 15’teki mini_agent.py’de modelle konuşan tek kapı ask_llm(messages, tools) idi. Bu bölümdeki bütün agent’lar aynı kapıyı kullanıyor. Onu lib/llm.py’ye taşıyıp üstüne iki küçük yardımcı ekliyoruz:

**Code 16.5**

```python
# lib/llm.py
import json

def ask_llm(messages, tools=None):
    """The adapter from Chapter 15: calls your assistant's API and returns the reply as text."""
    raise NotImplementedError("connect ask_llm to your own assistant")

def ask_text(prompt, system=""):
    return ask_llm([{"role": "system", "content": system},
                    {"role": "user", "content": prompt}])

def ask_json(prompt, system=""):
    return json.loads(ask_text(prompt + "\nReply with JSON only.", system))
```

> morning_agent.py üç parçadan oluşuyor. Birinci parça sabit bir workflow: Eşiklere bakan kontroller kuraldır, yorum değil. İkinci parça küçük bir ReAct döngüsü: Model bulgulara bakıp runbook’taki ek kontrollerden birini seçer, sonucu okur, gerekirse bir…

**Code 16.6**

```python
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
from mcp_server import ariza, kalite  # the tools from 16.2

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
    "incident_lookup": None,         # calls the ariza tool
    "late_step": """
        SELECT step, MAX(ts) AS finished_at FROM ops.pipeline_log
        WHERE run_date = ? GROUP BY step ORDER BY finished_at DESC LIMIT 3""",
}


def fixed_checks(day: date) -> list[dict]:
    """Workflow part: threshold checks are done by rules; the model stays out."""
    findings = []
    for r in kalite()["problems"]:                  # also updates quality.check_results
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
        return ariza(log_date=day.isoformat())
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
```

### 16.4 Fan-out: kaynak başına bir agent ile metadata

> Tablo 16.4 — Fan-out: kaynak başına alt agent

**Code 16.7**

```python
"""fanout_metadata.py - builds metadata with one sub-agent per source."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

from lib.llm import ask_json
from mcp_server import katalog

GROUPS = yaml.safe_load(open("governance/source_groups.yaml"))   # the table above
MAX_WORKERS = 4                    # at most four sub-agents at once (Chapter 17 limit: 6)
TOKEN_BUDGET = 200_000             # pipeline_agent's budget; a cap for the whole run

SUB_AGENT_RULES = """You look only at the metadata of the source you were given.
You may draft empty descriptions; mark every draft as description_source: ai_draft.
Do not invent a meaning that is not in the source document; if unsure, leave it empty.
Never change the technical fields (type, null rate, distinct count)."""


def sub_agent(group: str, tables: list[str], guide_text: str) -> dict:
    meta = katalog(tables=tables)                       # rule-based metadata first
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


def find_conflicts(results: list[dict]) -> list[dict]:
    seen, out = {}, []
    for r in results:
        for d in r["drafts"]:
            key = d["column_name"]                          # same name, different table
            if key in seen and seen[key]["text"] != d["description"]:
                out.append({"column": key, "a": seen[key], "b": d})
            seen.setdefault(key, {"group": r["group"], "text": d["description"]})
    return out
```

### 16.5 Yönetici agent ve insana sorma kuralları

> Yönetici agent bir hedef alır (“bz_returns kaynağını platforma al”), hazır oyun planlarından (playbook) birini seçer, adımları alt agent’lara dağıtır ve her adımın sonucuna göre devam eder ya da durur. Kendisi hiçbir aracı doğrudan çağırmaz; işi alt…

**Code 16.8**

```python
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
```

### 16.6 Mühendislik araç kiti ve veri ürünü vitrini

> Altı sayfanın beşi zaten var olan dosyalardan kural tabanlı üretiliyor. AI yalnızca iki yerde devrede: Her sayfanın başına “bu sayfa ne anlatıyor” diye iki cümlelik bir giriş yazıyor ve call graph’te fonksiyonların docstring’i yoksa bir satırlık açıklama…

**Code 16.9**

```python
"""build_toolkit_site.py - builds the engineering toolkit site from the repo and metadata."""
import ast
import html
from pathlib import Path

import duckdb
import yaml

from lib.llm import ask_text
from ch05_architecture.architecture_to_mermaid import to_mermaid as arch_to_mermaid

SITE = Path("site")
PAGE = """<!doctype html><meta charset="utf-8"><title>{title}</title>
<script type="module">import m from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs"; m.initialize({{startOnLoad:true}});</script>
<h1>{title}</h1><p>{intro}</p>{body}"""


def call_graph() -> str:
    edges = set()
    for py in Path(".").glob("ch*/**/*.py"):
        tree = ast.parse(py.read_text())
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call)]:
                name = getattr(call.func, "id", getattr(call.func, "attr", None))
                if name and name[0].islower():
                    edges.add(f"  {py.stem}.{fn.name} --> {name}")
    return "graph LR\n" + "\n".join(sorted(edges))


def data_model() -> str:
    lines = ["erDiagram"]
    for f in sorted(Path("metadata").glob("gold.*.yaml")):
        m = yaml.safe_load(f.read_text())
        cols = "\n".join(f"    {c['type']} {c['name']}" for c in m["columns"][:8])
        lines.append(f"  {m['table']} {{\n{cols}\n  }}")
        for fk in m.get("foreign_keys", []):
            lines.append(f"  {fk['to']} ||--o{{ {m['table']} : {fk['column']}")
    return "\n".join(lines)


def quality_matrix(db="data/meridian.duckdb") -> str:
    df = duckdb.connect(db, read_only=True).sql("""
        PIVOT (SELECT check_name, CAST(checked_at AS DATE) AS d, status
               FROM quality.check_results WHERE checked_at >= current_date - 14)
        ON d USING first(status)""").df()
    return df.to_html(index=False).replace(">fail<", ' class="fail">fail<')


def page(name: str, title: str, body: str, facts: str) -> None:
    intro = ask_text(f"Write a plain two-sentence introduction for this page. Use only "
                     f"these facts and do not invent numbers: {facts}")
    (SITE / f"{name}.html").write_text(PAGE.format(title=title, intro=html.escape(intro), body=body))


def run() -> dict:
    SITE.mkdir(exist_ok=True)
    mermaid = lambda s: f'<pre class="mermaid">{s}</pre>'
    page("architecture", "Architecture", mermaid(arch_to_mermaid(yaml.safe_load(open("architecture.yaml")))), "sources and layers")
    page("lineage", "Lineage", mermaid(Path("metadata/lineage.mmd").read_text()), "from gold back to bronze")
    page("call_graph", "Call graph", mermaid(call_graph()), "Python function calls")
    page("data_model", "Data model", mermaid(data_model()), "gold dimensions and facts")
    page("quality", "Quality matrix", quality_matrix(), "quality results for the last 14 days")
    page("catalog", "Catalog", Path("metadata/catalog.html").read_text(), "table and column descriptions")
    build_product_page("products/meridian_sales.yaml")
    return {"pages": sorted(p.name for p in SITE.glob("*.html"))}
```

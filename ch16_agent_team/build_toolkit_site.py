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
    page("architecture", "Architecture", mermaid(arch_to_mermaid(yaml.safe_load(open("ch05_architecture/architecture.yaml")))), "sources and layers")
    page("lineage", "Lineage", mermaid(Path("metadata/lineage.mmd").read_text()), "from gold back to bronze")
    page("call_graph", "Call graph", mermaid(call_graph()), "Python function calls")
    page("data_model", "Data model", mermaid(data_model()), "gold dimensions and facts")
    page("quality", "Quality matrix", quality_matrix(), "quality results for the last 14 days")
    page("catalog", "Catalog", Path("metadata/catalog.html").read_text(), "table and column descriptions")
    build_product_page("products/meridian_sales.yaml")
    return {"pages": sorted(p.name for p in SITE.glob("*.html"))}


# --------------------------------------------------------------------------- repo: completion
def build_product_page(card_path: str) -> None:
    """Data product showcase (Chapter 16.6): the card, its metrics and a 14-day quality summary."""
    card = yaml.safe_load(open(card_path, encoding="utf-8"))
    metrics = list(yaml.safe_load_all(open(card["metrics"], encoding="utf-8")))
    rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>"
                   for k, v in card.items() if k != "name")
    mrows = "".join(f"<li><b>{html.escape(m['metric'])}</b>: {html.escape(m['description'])} "
                    f"<code>{html.escape(m['expression'])}</code></li>" for m in metrics)
    body = (f"<table border='1'>{rows}</table><h2>Metrics</h2><ul>{mrows}</ul>"
            f"<h2>Quality, last 14 days</h2>{quality_matrix()}")
    page("product_" + Path(card_path).stem, card["name"], body, f"data product card {card['name']}")


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))

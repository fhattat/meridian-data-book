"""extract_metadata.py: builds table metadata from the data and the source guide."""
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
import duckdb, yaml

DB = "data/meridian.duckdb"
GUIDE = Path("ref/source_guide.yaml")
OWNERS = Path("governance/owners.yaml")
OUT = Path("metadata")

PII_RULES = [
    ("direct", r"(^|_)(email|phone|first_name|last_name|full_name|street|address)(_|$)"),
    ("indirect", r"(^|_)(birth|zip|ip|device)(_|$)"),
    ("free_text", r"(^|_)(body|notes|subject|message)(_|$)"),
]

def pii_label(column):
    for label, pattern in PII_RULES:
        if re.search(pattern, column.lower()):
            return label
    return None

def load_yaml(path):
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def describe(con, schema, table, guide, owners):
    stats = con.execute(f"SUMMARIZE {schema}.{table}").fetchall()
    names = [d[0] for d in con.description]
    row_count = con.execute(f"SELECT COUNT(*) FROM {schema}.{table}").fetchone()[0]
    g = guide.get("tables", {}).get(table, {})
    columns = []
    for raw in stats:
        s = dict(zip(names, raw))
        col = s["column_name"]
        gc = g.get("columns", {}).get(col, {})
        label = pii_label(col)
        samples = None
        if label is None:  # no sample values for personal data
            samples = [str(r[0]) for r in con.execute(
                f'SELECT DISTINCT "{col}" FROM {schema}.{table} WHERE "{col}" IS NOT NULL LIMIT 3'
            ).fetchall()]
        columns.append({
            "name": col,
            "type": s["column_type"],
            "null_pct": round(float(s["null_percentage"] or 0), 2),
            "approx_distinct": int(s["approx_unique"] or 0),
            "sample_values": samples,
            "pii": label,
            "description": gc.get("description"),          # stays None if missing
            "description_source": "source_guide" if gc.get("description") else None,
            "allowed_values": gc.get("allowed_values"),
        })
    o = owners.get(f"{schema}.{table}", {})
    return {
        "table": f"{schema}.{table}",
        "row_count": row_count,
        "description": g.get("description"),
        "description_source": "source_guide" if g.get("description") else None,
        "domain": o.get("domain"),
        "owner": o.get("owner"),
        "steward": o.get("steward"),
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "columns": columns,
    }

from html import escape

SQL_DIRS = [Path("ch09_medallion/sql/silver/duckdb"), Path("ch11_modeling/sql/gold")]
CREATE = re.compile(r"CREATE\s+OR\s+REPLACE\s+(?:TABLE|VIEW)\s+([\w.]+)", re.I)
REF = re.compile(r"\b(?:FROM|JOIN)\s+((?:bronze|silver|gold|ref)\.\w+)", re.I)

def lineage_from_sql():
    """Extracts (source, target) edges from the SQL files."""
    edges = set()
    for d in SQL_DIRS:
        for f in sorted(d.glob("*.sql")):
            parts = CREATE.split(f.read_text(encoding="utf-8"))
            for target, body in zip(parts[1::2], parts[2::2]):
                for src in REF.findall(body):
                    if src.lower() != target.lower():
                        edges.add((src.lower(), target.lower()))
    return sorted(edges)

def downstream(edges, node):
    """Impact analysis: every table fed by node."""
    found, todo = set(), [node]
    while todo:
        cur = todo.pop()
        for src, dst in edges:
            if src == cur and dst not in found:
                found.add(dst)
                todo.append(dst)
    return sorted(found)

def to_mermaid(edges, keep=None):
    lines = ["flowchart LR"]
    for src, dst in edges:
        if keep and not ({src, dst} & keep):
            continue
        a, b = src.replace(".", "_"), dst.replace(".", "_")
        lines.append(f'  {a}["{src}"] --> {b}["{dst}"]')
    return "\n".join(lines)

def catalog_html(metas):
    rows = []
    for m in metas:
        missing = sum(1 for c in m["columns"] if not c["description"])
        rows.append(f"<tr><td>{escape(m['table'])}</td><td>{escape(str(m.get('owner') or '-'))}</td>"
                    f"<td>{m['row_count']}</td><td>{len(m['columns'])}</td><td>{missing}</td></tr>")
    return ("<html><body><h1>Meridian data catalog</h1><table border='1'>"
            "<tr><th>Table</th><th>Owner</th><th>Rows</th><th>Columns</th><th>Missing descriptions</th></tr>"
            + "".join(rows) + "</table></body></html>")

def run(schema="silver", tables=None, env="local", out_dir="metadata"):
    if Path(out_dir).resolve() != OUT.resolve():
        raise PermissionError("the catalog tool writes only to the metadata/ folder")
    con = duckdb.connect(DB, read_only=True)          # read-only connection to the data
    guide, owners = load_yaml(GUIDE), load_yaml(OWNERS)
    if not tables:
        tables = [r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = ? ORDER BY 1", [schema]).fetchall()]
    # repo: also accept "schema.table" and patterns such as "gold.dim_*" (fan-out groups, Chapter 16.4)
    pairs = []
    for t in tables:
        sch, name = t.split(".", 1) if "." in t else (schema, t)
        if "*" in name:
            pairs += [(sch, r[0]) for r in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = ? AND table_name LIKE ? "
                "ORDER BY 1", [sch, name.replace("*", "%")]).fetchall()]
        else:
            pairs.append((sch, name))
    OUT.mkdir(exist_ok=True)
    metas = []
    for schema, t in pairs:
        meta = describe(con, schema, t, guide, owners)
        (OUT / f"{schema}.{t}.yaml").write_text(
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
        metas.append(meta)
    edges = lineage_from_sql()
    (OUT / "lineage.mmd").write_text(to_mermaid(edges), encoding="utf-8")
    (OUT / "catalog.html").write_text(catalog_html(metas), encoding="utf-8")
    return {
        "schema": sorted({s for s, _ in pairs}),
        "tables": [{"table": m["table"],
                    "columns": len(m["columns"]),
                    "missing_descriptions": sum(1 for c in m["columns"] if not c["description"]),
                    "pii_columns": sum(1 for c in m["columns"] if c["pii"])} for m in metas],
        "lineage_edges": len(edges),
        "output_dir": str(OUT),
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--env", default="local", choices=["local", "databricks"])
    p.add_argument("--schema", default="silver")
    p.add_argument("--tables", nargs="*")
    a = p.parse_args()
    print(json.dumps(run(schema=a.schema, tables=a.tables, env=a.env), indent=2))
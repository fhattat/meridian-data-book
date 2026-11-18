"""profile_source.py - profiles a source file before it is loaded.

Usage:
    python profile_source.py data/raw/bazaarly/csv/bz_products.csv --guide ref/source_guide.yaml

Output: reports/profile_<table>.html and contracts/<table>.yaml (draft).
Rule: technical facts come from the data, descriptions from the guide; anything not found stays empty.
"""
import argparse, csv, json, re
from pathlib import Path

import pandas as pd
import yaml

NULL_TOKENS = {"", "null", "n/a", "na", "-", "none"}
PII_NAME = re.compile(r"email|e_mail|phone|first_name|last_name|full_name|street|birth|zip|ip_|device")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
TYPES = [("integer", r"-?\d+"), ("decimal", r"-?\d+(\.\d+)?"),
         ("money_text", r"-?\$?\d{1,3}(,\d{3})*(\.\d+)?"),
         ("date_iso", r"\d{4}-\d{2}-\d{2}.*"), ("date_us", r"\d{1,2}/\d{1,2}/\d{2,4}.*")]


def sniff(path):
    """Guess the encoding and delimiter (a guess, not a certainty)."""
    raw = Path(path).read_bytes()[:20000]
    try:
        text, encoding = raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, encoding = raw.decode("cp1252"), "windows-1252"
    delimiter = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;|\t").delimiter
    return encoding, delimiter


def infer_type(values):
    for name, pattern in TYPES:
        if len(values) and values.str.fullmatch(pattern).mean() > 0.95:
            return name
    return "text"


def pii_label(col, values):
    if col.lower() in ("body", "notes", "description") and values.str.contains(PHONE).mean() > 0:
        return "free_text"
    if PII_NAME.search(col.lower()) or values.str.fullmatch(EMAIL.pattern).mean() > 0.5:
        return "indirect" if re.search(r"birth|zip|ip_|device", col.lower()) else "direct"
    return None


def mask(v):
    return v[0] + "***" + (v[v.find("@"):] if "@" in v else "")


def profile_column(df, col, guide):
    s = df[col]
    is_null = s.str.strip().str.lower().isin(NULL_TOKENS)
    values = s[~is_null]
    pii = pii_label(col, values)
    info = guide.get(col, {})
    unknown = sorted(set(values) - set(info["allowed_values"])) if "allowed_values" in info else []
    return {
        "column": col,
        "type_guess": infer_type(values),
        "null_rate": round(float(is_null.mean()), 3),
        "null_tokens": sorted(set(s[is_null].str.strip())),
        "distinct": int(values.nunique()),
        "max_len": int(values.str.len().max()) if len(values) else 0,
        "pii": pii,
        "sample": [mask(v) if pii else v for v in values.drop_duplicates().head(3)],
        "description": info.get("description", ""),            # empty if not in the guide
        "open_question": f"{', '.join(unknown)}: meaning not documented" if unknown else "",
    }


def run(path, table=None, guide=None, out_dir="."):
    """Called by the agent tool 'profile'. Read-only; writes only reports."""
    table = table or Path(path).stem
    guide = (yaml.safe_load(Path(guide).read_text()) or {}).get("tables", {}).get(table, {}).get("columns", {}) if guide else {}
    encoding, delimiter = sniff(path)
    df = pd.read_csv(path, sep=delimiter, encoding=encoding, dtype=str, keep_default_na=False)
    cols = [profile_column(df, c, guide) for c in df.columns]
    first = [str(v).strip().lower() for v in df.iloc[0]] if len(df) else []
    name_cols = [c for c in df.columns if "name" in c.lower()]
    twins = {}
    if name_cols:
        key = df[name_cols[0]].str.strip().str.lower()
        twins = {k: int(v) for k, v in key.value_counts().items() if v > 1}
    test_rows = df.apply(lambda r: r.str.contains(r"\btest\b", case=False).any(), axis=1)
    summary = {
        "table": table, "rows": len(df), "encoding": encoding, "delimiter": delimiter,
        "header_in_data": bool(sum(v == c.lower() for v, c in zip(first, df.columns)) >= len(df.columns) / 2),
        "candidate_keys": [c["column"] for c in cols if c["null_rate"] == 0 and c["distinct"] == len(df)],
        "empty_columns": [c["column"] for c in cols if c["null_rate"] == 1],
        "long_text_columns": [c["column"] for c in cols if c["max_len"] > 200],
        "pii_columns": {c["column"]: c["pii"] for c in cols if c["pii"]},
        "twin_name_suspects": twins,
        "test_row_suspects": int(test_rows.sum()),
        "open_questions": [f"{c['column']} -> {c['open_question']}" for c in cols if c["open_question"]],
    }
    out = Path(out_dir)
    (out / "reports").mkdir(parents=True, exist_ok=True)
    (out / "contracts").mkdir(parents=True, exist_ok=True)
    html = f"<h1>Profile: {table}</h1><pre>{json.dumps(summary, indent=2, ensure_ascii=False)}</pre>"
    (out / "reports" / f"profile_{table}.html").write_text(html + pd.DataFrame(cols).to_html(index=False))
    contract = {"table": table, "owner": "", "grain": "", "primary_key": summary["candidate_keys"][:1],
                "columns": [{"name": c["column"], "type": c["type_guess"], "nullable": bool(c["null_rate"] > 0),
                             "description": c["description"], "pii": c["pii"] or False,
                             **({"open_question": c["open_question"]} if c["open_question"] else {})}
                            for c in cols]}
    (out / "contracts" / f"{table}.yaml").write_text(yaml.safe_dump(contract, allow_unicode=True, sort_keys=False))
    return summary


DEFAULT_SOURCES = [  # repo: profiled when no path is given (run_pipeline.py step "profile")
    "data/raw/meridian/mm_products.csv", "data/raw/meridian/mm_loyalty_members.csv",
    "data/raw/bazaarly/csv/bz_products.csv", "data/raw/bazaarly/csv/bz_users.csv",
    "data/raw/bazaarly/csv/bz_cities.csv", "data/raw/bazaarly/csv/dim_order.csv",
]

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", help="source file; without it the DEFAULT_SOURCES are profiled")
    p.add_argument("--table")
    p.add_argument("--guide")
    p.add_argument("--out", default=".")
    p.add_argument("--env", choices=["local", "databricks"], default="local")
    p.add_argument("--size", default="small")          # repo: passed by run_pipeline.py, not used here
    a = p.parse_args()
    if a.path is None:
        # Drafts go to reports/drafts/ so they never overwrite the reviewed files in contracts/.
        guide = a.guide or "ref/source_guide.yaml"
        result = {Path(s).stem: run(s, None, guide, "reports/drafts") for s in DEFAULT_SOURCES}
        print(json.dumps({t: {k: r[k] for k in ("rows", "pii_columns", "open_questions", "test_row_suspects")}
                          for t, r in result.items()}, indent=2, ensure_ascii=False))
        raise SystemExit(0)
    path = a.path if a.env == "local" else f"/Volumes/meridian/raw/landing/{a.path}"
    print(json.dumps(run(path, a.table, a.guide, a.out), indent=2, ensure_ascii=False))

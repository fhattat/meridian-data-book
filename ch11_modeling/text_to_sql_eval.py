# ch11_modeling/text_to_sql_eval.py
"""Asks the model the same ten questions with different contexts and compares the results with the answer key.

Usage: python ch11_modeling/text_to_sql_eval.py --env local --layer gold
          python ch11_modeling/text_to_sql_eval.py --env local --layer bronze
          (Chapter 18: --layer bronze --guide ref/source_guide.yaml)
"""
import argparse, json, yaml, duckdb

def ask_llm(system: str, question: str) -> str:
    """Call your model's API here; return only the SQL text."""
    raise NotImplementedError

def schema_context(con, layer: str, guide: str | None) -> str:
    rows = con.execute(
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = ? ORDER BY table_name, ordinal_position", [layer]
    ).fetchall()
    text = "\n".join(f"{t}.{c} {d}" for t, c, d in rows)
    if layer == "gold":
        text += "\n\n" + open("ch11_modeling/gold_grain.md").read()  # grain and metric definitions
    if guide:
        text += "\n\n" + open(guide).read()                         # e.g. ref/source_guide.yaml
    return text

def is_correct(result, expected, tolerance) -> bool:
    if isinstance(expected, (int, float)):
        return result is not None and abs(float(result) - expected) <= abs(expected) * tolerance
    return result == expected

def run(layer: str = "gold", guide: str | None = None, repeats: int = 3,
        db: str = "data/meridian.duckdb") -> dict:
    con = duckdb.connect(db, read_only=True)
    system = ("You are a data analyst. Return DuckDB SQL only.\n"
              + schema_context(con, layer, guide))
    answers = json.load(open("data/raw/answer_key.json"))   # generated from control_totals.json
    results = []
    for q in yaml.safe_load(open("ch11_modeling/questions.yaml")):
        for i in range(repeats):
            sql = ask_llm(system, q["question"])
            try:
                value = con.execute(sql).fetchone()[0]
                ok = is_correct(value, answers[q["id"]], q.get("tolerance", 0))
                error = None
            except Exception as exc:
                value, ok, error = None, False, str(exc)[:200]
            results.append({"id": q["id"], "try": i + 1, "ok": ok, "error": error, "sql": sql})
    score = sum(r["ok"] for r in results) / len(results)
    return {"layer": layer, "guide": guide, "repeats": repeats,
            "score": round(score, 3), "results": results}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="local", choices=["local", "databricks"])
    ap.add_argument("--layer", default="gold", choices=["bronze", "gold"])
    ap.add_argument("--guide", default=None, help="description file to add to the schema context")
    ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    out = run(layer=a.layer, guide=a.guide, repeats=a.repeats)   # on Databricks, a SQL warehouse connection instead of db
    print(json.dumps({k: v for k, v in out.items() if k != "results"}, ensure_ascii=False))

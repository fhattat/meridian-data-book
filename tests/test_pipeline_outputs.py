"""After run_pipeline.py: gold keeps the number and answers the ten questions (Chapters 11, 17, 18)."""
import json
import re
from pathlib import Path

import pytest

QUERIES = Path("ch11_modeling/reference_answers.sql").read_text(encoding="utf-8")
ANSWERS = json.loads(Path("data/raw/answer_key.json").read_text())


def _queries():
    parts = re.split(r"^-- @(q\d\d).*$", QUERIES, flags=re.M)[1:]
    return list(zip(parts[0::2], parts[1::2]))


@pytest.mark.parametrize("qid,sql", _queries())
def test_reference_answer_matches_answer_key(con, qid, sql):
    value = con.execute(sql.strip().rstrip(";")).fetchone()[0]
    expected = ANSWERS[qid]
    if isinstance(expected, float):
        assert float(value) == pytest.approx(expected, abs=0.011)
    elif isinstance(expected, list):
        assert value == ", ".join(expected)
    else:
        assert value == expected


def test_gold_reconciles_with_control_totals(con):
    from lib.reconcile import reconcile
    df = con.execute("SELECT source_company, period, amount_usd FROM gold.fact_sales_monthly").df()
    df["amount_usd"] = df["amount_usd"].astype(float)
    assert reconcile(df, "data/raw/control_totals.json", step="test")["status"] == "pass"


def test_no_test_records_in_fact_sales(con):
    n = con.execute("""SELECT COUNT(*) FROM gold.fact_sales
                       WHERE order_id LIKE '999%' AND source_company = 'MM'""").fetchone()[0]
    assert n == 0


def test_twins_are_not_survivors(con):
    n = con.execute("SELECT COUNT(*) FROM silver.product_xref WHERE NOT is_survivor").fetchone()[0]
    assert n == 15


def test_no_personal_data_columns_in_gold(con):
    cols = {r[0] for r in con.execute("""SELECT column_name FROM information_schema.columns
                                         WHERE table_schema = 'gold'""").fetchall()}
    assert not cols & {"email", "phone", "first_name", "last_name", "birth_date", "email_norm"}


def test_rag_index_quarantined_the_injection(con):
    tables = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='gold'").fetchall()}
    if "rag_chunks" not in tables:
        pytest.skip("run ch12_serving/build_rag_index.py first")
    n = con.execute("""SELECT COUNT(*) FROM quality.quarantine
                       WHERE table_name = 'gold.rag_chunks' AND row_payload::VARCHAR LIKE '%T-18842%'""").fetchone()[0]
    assert n >= 1

"""Small-data tests for lib/ (Chapter 10, 16, 17): no database needed."""
import os

import pandas as pd
import pytest

from lib.io import _check_scope
from lib.reconcile import ReconcileError, reconcile, safe_left_join
from lib.schema_gate import schema_gate

CONTRACT = {"columns": [{"name": "order_id"}, {"name": "status_code"}, {"name": "notes", "required": False}]}


def test_schema_gate_rename_is_held():
    r = schema_gate(["order_id", "status", "notes"], CONTRACT)       # status_code -> status (2027-04-15)
    assert r == {"decision": "hold", "missing": ["status_code"], "unexpected": ["status"]}


def test_schema_gate_new_column_passes_with_warning():
    assert schema_gate(["order_id", "status_code", "extra"], CONTRACT)["decision"] == "pass_with_warning"


def test_safe_left_join_stops_on_duplicate_right_key():
    left = pd.DataFrame({"name_norm": ["a", "b"], "amount_usd": [10.0, 5.0]})
    right = pd.DataFrame({"name_norm": ["a", "a "] , "product_id": ["1", "2"]})
    right["name_norm"] = right["name_norm"].str.strip()                # the twin with a trailing space
    with pytest.raises(ReconcileError):
        safe_left_join(left, right, on="name_norm", measure="amount_usd", step="test")


def test_safe_left_join_keeps_the_number():
    left = pd.DataFrame({"k": ["a", "b", "c"], "amount_usd": [1.0, 2.0, 3.0]})
    right = pd.DataFrame({"k": ["a", "b"], "v": [1, 2]})
    out = safe_left_join(left, right, on="k", measure="amount_usd", step="test")
    assert len(out) == 3 and out["amount_usd"].sum() == 6.0


def test_reconcile_reports_a_difference(tmp_path):
    p = tmp_path / "ct.json"
    p.write_text('{"net_sales_usd": {"MM": {"2026-01": 100.0}}}')
    df = pd.DataFrame({"source_company": ["MM"], "period": ["2026-01"], "amount_usd": [99.0]})
    assert reconcile(df, p, step="t", raise_on_fail=False)["status"] == "fail"
    df["amount_usd"] = 100.0
    assert reconcile(df, p, step="t")["status"] == "pass"


def test_write_scope_blocks_other_layers(monkeypatch):
    monkeypatch.setenv("MERIDIAN_WRITE_SCOPE", "silver")
    monkeypatch.setenv("MERIDIAN_TOOL", "temizlik")
    _check_scope("silver.pos_lines")
    with pytest.raises(PermissionError):
        _check_scope("gold.fact_sales")

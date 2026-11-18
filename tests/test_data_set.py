"""The synthetic data set has the traps the book talks about (Appendix D) and its control files."""
import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")


def test_control_totals_structure():
    ct = json.loads((RAW / "control_totals.json").read_text())
    assert set(ct["net_sales_usd"]) == {"MM", "BZ"}
    assert len(ct["net_sales_usd"]["MM"]) == 30                      # 2025-01 .. 2027-06
    assert all(v > 0 for v in ct["net_sales_usd"]["BZ"].values())


def test_answer_key_has_ten_answers():
    ak = json.loads((RAW / "answer_key.json").read_text())
    assert [f"q{i:02d}" for i in range(1, 11)] == sorted(k for k in ak if k.startswith("q"))


def test_black_friday_resend_is_an_exact_copy():                     # trap 8
    a = RAW / "meridian/pos/pos_20251128.csv"
    assert a.read_bytes() == (RAW / "meridian/pos/pos_20251128_resend.csv").read_bytes()


def test_missing_day_is_in_the_wrong_folder():                       # trap 9
    assert not (RAW / "meridian/pos/pos_20260209.csv").exists()
    assert (RAW / "meridian/pos_late/pos_20260209.csv").exists()


def test_pos_file_is_cp1252_with_semicolons():                       # trap 1
    first = (RAW / "meridian/pos/pos_20250102.csv").read_bytes().decode("cp1252").splitlines()[0]
    assert first.startswith("H;") and ";$" in first.replace(";-$", ";$")


def test_channel_code_50_is_not_in_the_mapping():                    # trap 22
    codes = pd.read_csv("ref/channel_codes.csv", dtype=str)["channel_code"]
    assert "50" not in set(codes)


def test_status_column_renamed_on_2027_04_15():                      # trap 28
    before = pd.read_csv(RAW / "bazaarly/bz_orders_2027/bz_orders_20270414.csv", nrows=0).columns
    after = pd.read_csv(RAW / "bazaarly/bz_orders_2027/bz_orders_20270415.csv", nrows=0).columns
    assert "status_code" in before and "status" in after and "status_code" not in after


def test_hidden_instruction_ticket_exists():                         # trap 30 / Chapter 17
    text = (RAW / "bazaarly/bz_support_tickets.jsonl").read_text(encoding="utf-8")
    assert '"T-18842"' in text and "ignore previous instructions" in text


def test_emails_are_reserved_example_domains():
    users = pd.read_csv(RAW / "bazaarly/csv/bz_users.csv", dtype=str)
    domains = users["email"].str.lower().str.split("@").str[-1]
    assert set(domains) <= {"example.com", "example.net", "example.org"}

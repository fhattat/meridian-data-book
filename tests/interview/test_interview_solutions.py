"""Ek C SQL alıştırmalarının çözümlerini küçük bir test verisiyle doğrular.

Çalıştırma (depo kökünden):
    pytest tests/interview -q

Varsayılan olarak DuckDB kullanılır (kitabın yerel motoru). DuckDB kurulu değilse
aynı testler Python'un yerleşik sqlite3 modülüyle çalışır; çözümler bu yüzden
DuckDB, Databricks SQL ve SQLite'ta aynı çalışan taşınabilir SQL ile yazıldı.
"""
from pathlib import Path
import re

import pytest

HERE = Path(__file__).parent
SOLUTIONS = HERE / "solutions"
SCHEMAS = ["bronze", "silver", "gold"]


def _statement(path: Path) -> str:
    """Dosyadaki ilk SQL ifadesini döner; yorum satırlarını atar."""
    text = re.sub(r"--[^\n]*", "", path.read_text(encoding="utf-8"))
    return text.split(";")[0].strip()


def _fixture_statements() -> list[str]:
    text = re.sub(r"--[^\n]*", "", (HERE / "fixture.sql").read_text(encoding="utf-8"))
    return [s.strip() for s in text.split(";") if s.strip()]


class Engine:
    def __init__(self):
        try:
            import duckdb
            self.name = "duckdb"
            self.con = duckdb.connect(":memory:")
            for s in SCHEMAS:
                self.con.execute(f"CREATE SCHEMA {s}")
        except ImportError:
            import sqlite3
            self.name = "sqlite"
            self.con = sqlite3.connect(":memory:")
            for s in SCHEMAS:
                self.con.execute(f"ATTACH DATABASE ':memory:' AS {s}")
        for stmt in _fixture_statements():
            self.con.execute(stmt)

    def rows(self, sql: str) -> list[tuple]:
        return [tuple(r) for r in self.con.execute(sql).fetchall()]


@pytest.fixture(scope="module")
def db():
    return Engine()


def run(db, name):
    return db.rows(_statement(SOLUTIONS / name))


def test_q01_orders_without_items(db):
    rows = run(db, "q01_orders_without_items.sql")
    assert [(r[0], int(r[3])) for r in rows] == [("O4", 0), ("O6", 1)]


def test_q02_current_customer(db):
    rows = run(db, "q02_current_customer.sql")
    assert [(r[0], r[1]) for r in rows] == [("K2", "BZ-U-1"), ("K1b", "MM-M-1")]


def test_q03_net_sales_by_region_2026(db):
    rows = [(r[0], round(float(r[1]), 2)) for r in run(db, "q03_net_sales_by_region_2026.sql")]
    assert rows == [("Northeast", 170.00), ("West", 165.00), ("Online (Bazaarly)", 40.00)]


def test_q04_bazaarly_orders_march_2027(db):
    rows = run(db, "q04_bazaarly_orders_march_2027.sql")
    assert [tuple(int(v) for v in r) for r in rows] == [(5, 4)]


def test_q05_header_vs_lines(db):
    rows = [(r[0], round(float(r[3]), 2)) for r in run(db, "q05_header_vs_lines.sql")]
    assert rows == [("O4", 10.00), ("O3", 5.00)]  # O7'nin 0,01'lik farkı tolerans içinde


def test_q06_customers_in_both(db):
    assert [int(r[0]) for r in run(db, "q06_customers_in_both.sql")] == [2]  # ayla, dora; test hariç


def test_q07_top3_categories_per_store(db):
    rows = [(r[0], r[1], int(r[3])) for r in run(db, "q07_top3_categories_per_store.sql")]
    assert rows == [
        ("Bazaarly Online", "Electronics", 1),
        ("Boston Back Bay", "Toys", 1),
        ("Boston Back Bay", "Electronics", 2),
        ("Boston Back Bay", "Home", 3),
        ("Seattle Downtown", "Electronics", 1),
        ("Seattle Downtown", "Home", 1),
        ("Seattle Downtown", "Personal Care", 3),
    ]


def test_q08_bronze_vs_silver_pos(db):
    rows = [(r[0], int(r[1])) for r in run(db, "q08_bronze_vs_silver_pos.sql")]
    assert rows == [("R2", 1)]  # R3 test fişi silver'da işaretli, kayıp değil

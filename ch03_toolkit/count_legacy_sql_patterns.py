import re
from pathlib import Path
from collections import Counter

patterns = {
    "SELECT *": r"select\s+\*",
    "INNER JOIN": r"\binner\s+join\b",
    "LEFT JOIN": r"\bleft\s+(outer\s+)?join\b",
    "CTE (WITH)": r"^\s*with\b",
    "CASE WHEN": r"\bcase\s+when\b",
    "ROW_NUMBER": r"\brow_number\s*\(",
    "DISTINCT": r"\bdistinct\b",
}
counts = Counter()
for f in Path("data/raw/ops/sql_legacy").glob("*.sql"):
    text = f.read_text(encoding="utf-8", errors="replace").lower()
    for name, pat in patterns.items():
        counts[name] += len(re.findall(pat, text, flags=re.MULTILINE))
print(counts.most_common())

"""compare_outputs.py — compares the output of the four engines with the same measures."""
import pandas as pd

def fingerprint(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "distinct_receipts": int(df["receipt_no"].nunique()),
        "total_usd": round(float(df["receipt_total_usd"].astype(float).sum()), 2),
        "null_ts": int(df["receipt_ts_utc"].isna().sum()),
        "min_ts": str(df["receipt_ts_utc"].min()),
        "max_ts": str(df["receipt_ts_utc"].max()),
    }

def compare(outputs: dict[str, pd.DataFrame], reference: str = "duckdb") -> pd.DataFrame:
    prints = {name: fingerprint(df) for name, df in outputs.items()}
    table = pd.DataFrame(prints).T
    table["matches_reference"] = [prints[name] == prints[reference] for name in table.index]
    return table

# outputs = {"duckdb": receipts_duckdb, "pandas": receipts_pd,
#            "polars": receipts_pl.to_pandas(), "pyspark": receipts_spark.toPandas()}
# print(compare(outputs))

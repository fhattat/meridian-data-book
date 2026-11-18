"""benchmark_engines.py: runs the same query with pandas, Polars and DuckDB and compares timings.

Usage:
    python benchmark_engines.py data/layers/silver/pos_lines.parquet --runs 3
    python benchmark_engines.py sample.parquet --synthetic 5000000
"""
import argparse
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import polars as pl


def make_synthetic(path: Path, n_rows: int, seed: int = 2027) -> None:
    """Creates a synthetic file with the same column names when there is no silver output."""
    rng = np.random.default_rng(seed)
    days = rng.integers(0, 911, n_rows)  # between 2025-01-01 and 2027-06-30
    df = pd.DataFrame({
        "store_id": rng.choice([f"MM-{i:03d}" for i in range(1, 49)], n_rows),
        "receipt_local_date": pd.Timestamp("2025-01-01") + pd.to_timedelta(days, unit="D"),
        "amount_usd": rng.gamma(2.0, 30.0, n_rows).round(2),
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def run_pandas(path: Path):
    df = pd.read_parquet(path, columns=["store_id", "receipt_local_date", "amount_usd"])
    df["month"] = pd.to_datetime(df["receipt_local_date"]).dt.strftime("%Y-%m")
    return (df.groupby(["store_id", "month"], as_index=False)["amount_usd"].sum()
              .sort_values(["store_id", "month"]))


def run_polars(path: Path):
    return (pl.scan_parquet(path)
              .with_columns(pl.col("receipt_local_date").dt.strftime("%Y-%m").alias("month"))
              .group_by(["store_id", "month"])
              .agg(pl.col("amount_usd").sum())
              .sort(["store_id", "month"])
              .collect())


def run_duckdb(path: Path):
    return duckdb.sql(f"""
        SELECT store_id,
               strftime(receipt_local_date, '%Y-%m') AS month,
               SUM(amount_usd) AS amount_usd
        FROM read_parquet('{path.as_posix()}')
        GROUP BY ALL
        ORDER BY store_id, month
    """).df()


def benchmark(fn, path: Path, runs: int):
    times, result = [], None
    for _ in range(runs):
        start = time.perf_counter()
        result = fn(path)
        times.append(time.perf_counter() - start)
    return min(times), len(result), float(result["amount_usd"].sum())


def main() -> None:
    parser = argparse.ArgumentParser(description="pandas vs Polars vs DuckDB timing")
    parser.add_argument("path", nargs="?", default="data/layers/silver/pos_lines.parquet")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--synthetic", type=int, default=0,
                        help="If the file is missing, generate this many rows of sample data")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        if not args.synthetic:
            raise SystemExit(f"{path} not found. Generate sample data with --synthetic 1000000.")
        make_synthetic(path, args.synthetic)

    print(f"{'engine':<8}{'best time (s)':>18}{'rows':>8}{'total':>18}")
    for name, fn in [("pandas", run_pandas), ("polars", run_polars), ("duckdb", run_duckdb)]:
        best, n_rows, total = benchmark(fn, path, args.runs)
        print(f"{name:<8}{best:>18.3f}{n_rows:>8}{total:>18,.2f}")


if __name__ == "__main__":
    main()

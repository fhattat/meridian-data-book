# pandas
import pandas as pd
df = pd.read_csv("data/raw/meridian/mm_loyalty_members.csv", dtype=str)
out = (df[df["MEMBER_NO"] != "999"]
       .groupby("STATE").size()
       .sort_values(ascending=False))

# Polars (lazy: runs when you call collect())
import polars as pl
out = (pl.scan_csv("data/raw/meridian/mm_loyalty_members.csv", infer_schema=False)
       .filter(pl.col("MEMBER_NO") != "999")
       .group_by("STATE").len()
       .sort("len", descending=True)
       .collect())

# DuckDB
import duckdb
out = duckdb.sql("""
    SELECT STATE, count(*) AS n
    FROM read_csv('data/raw/meridian/mm_loyalty_members.csv', all_varchar = true)
    WHERE MEMBER_NO <> '999'
    GROUP BY STATE ORDER BY n DESC
""").df()

# PySpark (spark is ready in a Databricks notebook)
from pyspark.sql import functions as F
df = (spark.read.option("header", True)
      .csv("/Volumes/meridian/raw/landing/mm_loyalty_members.csv"))
out = (df.filter(F.col("MEMBER_NO") != "999")
       .groupBy("STATE").count()
       .orderBy(F.desc("count")))

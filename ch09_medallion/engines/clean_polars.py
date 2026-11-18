import polars as pl

import duckdb  # named POS columns come from the view in 40_pos.sql
raw = duckdb.connect("data/meridian.duckdb", read_only=True).sql("SELECT * FROM bronze.mm_pos_named").pl()
stores = pl.read_parquet("data/layers/silver/stores.parquet").select("store_id", "iana_tz")

h = (
    raw.filter(pl.col("rec_type") == "H")
    .with_columns(
        pl.col("STORE_CD").str.strip_chars().alias("store_id"),
        pl.col("RECEIPT_TS").str.strip_chars()
          .str.strptime(pl.Datetime, "%m/%d/%Y %I:%M %p", strict=False).alias("ts_local"),
        pl.col("RECEIPT_TOTAL").str.replace_all(r"[$,]", "").str.strip_chars()
          .cast(pl.Decimal(12, 2), strict=False).alias("receipt_total_usd"),
    )
    .join(stores, on="store_id", how="left")
)

# Polars converts time zones with a single zone string, not per row; so we process one zone at a time.
parts = [
    h.filter(pl.col("iana_tz") == tz).with_columns(
        pl.col("ts_local").dt.replace_time_zone(tz, ambiguous="null", non_existent="null")
          .dt.convert_time_zone("UTC").dt.replace_time_zone(None).alias("receipt_ts_utc"))
    for tz in h["iana_tz"].drop_nulls().unique()
]
parts.append(h.filter(pl.col("iana_tz").is_null())
               .with_columns(pl.lit(None, dtype=pl.Datetime("us")).alias("receipt_ts_utc")))
receipts_pl = (pl.concat(parts)
               .select(pl.col("RECEIPT_NO").alias("receipt_no"), "receipt_ts_utc", "receipt_total_usd"))

import pandas as pd

import duckdb  # named POS columns come from the view in 40_pos.sql
raw = duckdb.connect("data/meridian.duckdb", read_only=True).sql("SELECT * FROM bronze.mm_pos_named").df()
stores = pd.read_parquet("data/layers/silver/stores.parquet")[["store_id", "iana_tz"]]

h = raw[raw["rec_type"] == "H"].copy()
h["store_id"] = h["STORE_CD"].str.strip()
h["ts_local"] = pd.to_datetime(h["RECEIPT_TS"].str.strip(), format="%m/%d/%Y %I:%M %p", errors="coerce")
h = h.merge(stores, on="store_id", how="left", validate="many_to_one")

def to_utc(ts, tz):
    if pd.isna(ts) or pd.isna(tz):
        return pd.NaT
    return ts.tz_localize(tz, ambiguous="NaT", nonexistent="NaT").tz_convert("UTC").tz_localize(None)

h["receipt_ts_utc"] = [to_utc(ts, tz) for ts, tz in zip(h["ts_local"], h["iana_tz"])]
h["receipt_total_usd"] = pd.to_numeric(
    h["RECEIPT_TOTAL"].str.replace(r"[$,]", "", regex=True).str.strip(), errors="coerce").round(2)
receipts_pd = h.rename(columns={"RECEIPT_NO": "receipt_no"})[["receipt_no", "receipt_ts_utc", "receipt_total_usd"]]

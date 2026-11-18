from pyspark.sql import functions as F

raw = spark.table("meridian.bronze.mm_pos_named")
stores = spark.table("meridian.silver.stores").select("store_id", "iana_tz")

receipts_spark = (
    raw.filter(F.col("rec_type") == "H")
    .withColumn("store_id", F.trim("STORE_CD"))
    .withColumn("ts_local", F.expr("try_to_timestamp(trim(RECEIPT_TS), 'MM/dd/yyyy hh:mm a')"))
    .join(stores, "store_id", "left")
    .withColumn("receipt_ts_utc", F.to_utc_timestamp("ts_local", F.col("iana_tz")))
    .withColumn("receipt_total_usd",
                F.expr("try_cast(regexp_replace(trim(RECEIPT_TOTAL), '[$,]', '') AS DECIMAL(12,2))"))
    .select(F.col("RECEIPT_NO").alias("receipt_no"), "receipt_ts_utc", "receipt_total_usd")
)

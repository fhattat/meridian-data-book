from pyspark.sql import functions as F

df = spark.table("meridian.silver.pos_lines")  # the Delta table built in Chapter 9
result = (df.groupBy("store_id", F.date_format("receipt_local_date", "yyyy-MM").alias("month"))
            .agg(F.sum("amount_usd").alias("amount_usd"))
            .orderBy("store_id", "month"))
result.agg(F.sum("amount_usd")).show()  # must equal the total from the other three engines

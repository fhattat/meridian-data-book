# ch12_serving/export_features.py
import duckdb

FEATURE_SQL = """
WITH tx AS (
    SELECT t.txn_id, t.user_id, t.device_id, t.card_country, t.ip_country,
           CAST(t.hour AS INTEGER)            AS hour,
           o.order_ts_utc,
           t.amount_usd,
           CAST(t.is_fraud AS BOOLEAN)        AS is_fraud
    FROM silver.payment_transactions t
    JOIN silver.bz_orders o USING (order_id)
)
SELECT
    txn_id, order_ts_utc, amount_usd,
    amount_usd / NULLIF(AVG(amount_usd) OVER (
        PARTITION BY user_id ORDER BY order_ts_utc
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)  AS amt_to_user_mean,
    hour BETWEEN 0 AND 4                                        AS is_night,
    card_country <> ip_country                                  AS country_mismatch,
    COUNT(user_id) OVER (
        PARTITION BY device_id ORDER BY order_ts_utc
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)       AS device_prior_txn,
    is_fraud
FROM tx
"""

def run(db_path: str = "data/meridian.duckdb") -> dict:
    """Builds the feature table, writes it to gold.ml_fraud_features and returns a summary."""
    con = duckdb.connect(db_path)
    con.execute(f"CREATE OR REPLACE TABLE gold.ml_fraud_features AS {FEATURE_SQL}")
    rows, frauds, null_ratio = con.execute("""
        SELECT COUNT(*), SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END),
               AVG(CASE WHEN amt_to_user_mean IS NULL THEN 1.0 ELSE 0 END)
        FROM gold.ml_fraud_features""").fetchone()
    return {"table": "gold.ml_fraud_features", "rows": rows,
            "fraud_rows": frauds, "first_txn_null_ratio": round(null_ratio, 4)}

if __name__ == "__main__":
    print(run())

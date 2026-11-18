-- 40_pos.sql
-- Chapter 8 left POS rows as rec_type + field_1…field_7; first we give the fields their source names.
CREATE OR REPLACE VIEW bronze.mm_pos_named AS
SELECT rec_type,
       field_1 AS RECEIPT_NO,
       CASE WHEN rec_type = 'H' THEN field_2 END AS STORE_CD,
       CASE WHEN rec_type = 'H' THEN field_3 END AS RECEIPT_TS,
       CASE WHEN rec_type = 'H' THEN field_4 END AS REGISTER_NO,
       CASE WHEN rec_type = 'H' THEN field_5 END AS MEMBER_NO,
       CASE WHEN rec_type = 'H' THEN field_6 END AS TENDER_TYPE,
       CASE WHEN rec_type = 'H' THEN field_7 END AS RECEIPT_TOTAL,
       CASE WHEN rec_type = 'L' THEN field_2 END AS LINE_NO,
       CASE WHEN rec_type = 'L' THEN field_3 END AS PROD_CD,
       CASE WHEN rec_type = 'L' THEN field_4 END AS QTY,
       CASE WHEN rec_type = 'L' THEN field_5 END AS UNIT_PRICE,
       CASE WHEN rec_type = 'L' THEN field_6 END AS DISC_AMT,
       CASE WHEN rec_type = 'L' THEN field_7 END AS LINE_AMT,
       _ingested_at, _source_file, _batch_id, _row_hash
FROM bronze.mm_pos_raw;

CREATE OR REPLACE TABLE silver.pos_receipts AS
WITH h AS (
  SELECT r.*, strptime(clean_text(r.RECEIPT_TS), '%m/%d/%Y %I:%M %p') AS ts_local
  FROM bronze.mm_pos_named r
  WHERE r.rec_type = 'H'
)
SELECT
  clean_text(h.RECEIPT_NO)                          AS receipt_no,
  clean_text(h.STORE_CD)                            AS store_id,
  timezone('UTC', timezone(s.iana_tz, h.ts_local))  AS receipt_ts_utc,
  CAST(h.ts_local AS DATE)                          AS receipt_local_date,
  clean_text(h.MEMBER_NO)                           AS member_no,
  clean_text(h.TENDER_TYPE)                         AS tender_type,
  to_usd_amount(h.RECEIPT_TOTAL)                    AS receipt_total_usd,
  COALESCE(clean_text(h.MEMBER_NO) IN (
    SELECT key_value FROM ref_test_records WHERE entity = 'mm_member'), FALSE) AS is_test,
  'MM'                                              AS source_company,
  h._source_file, h._batch_id
FROM h
LEFT JOIN silver.stores s ON s.store_id = clean_text(h.STORE_CD);

CREATE OR REPLACE TABLE silver.pos_lines AS
SELECT
  clean_text(l.RECEIPT_NO)                    AS receipt_no,
  CAST(clean_text(l.LINE_NO) AS INT)          AS line_no,
  h.store_id,
  clean_text(l.PROD_CD)                       AS product_id,
  CAST(clean_text(l.QTY) AS INT)              AS qty,
  to_usd_amount(l.LINE_AMT)                   AS amount_original,
  'USD'                                       AS currency,
  to_usd_amount(l.LINE_AMT)                   AS amount_usd,
  h.receipt_ts_utc,
  h.receipt_local_date,
  CAST(date_trunc('month', h.receipt_local_date) AS DATE) AS receipt_month,
  CAST(clean_text(l.QTY) AS INT) < 0          AS is_return,
  COALESCE(h.is_test, FALSE)                  AS is_test,
  'MM'                                        AS source_company
FROM bronze.mm_pos_named l
LEFT JOIN silver.pos_receipts h ON h.receipt_no = clean_text(l.RECEIPT_NO)
WHERE l.rec_type = 'L';
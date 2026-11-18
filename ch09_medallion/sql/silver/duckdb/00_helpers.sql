-- 00_helpers.sql
SET TimeZone = 'UTC';  -- Bazaarly times are UTC; pin the session, otherwise the machine's time zone is used

CREATE OR REPLACE MACRO clean_text(x) AS
  CASE WHEN TRIM(x) IN ('', 'NULL', 'N/A') THEN NULL ELSE TRIM(x) END;

CREATE OR REPLACE MACRO to_usd_amount(x) AS
  TRY_CAST(REPLACE(REPLACE(clean_text(x), '$', ''), ',', '') AS DECIMAL(12,2));

CREATE OR REPLACE VIEW ref_test_records  AS SELECT * FROM read_csv('ref/test_records.csv',  all_varchar = true);
CREATE OR REPLACE VIEW ref_state_aliases AS SELECT * FROM read_csv('ref/state_aliases.csv', all_varchar = true);

CREATE OR REPLACE TABLE silver.channel_codes AS
SELECT clean_text(channel_code) AS channel_code, clean_text(channel_name) AS channel_name
FROM read_csv('ref/channel_codes.csv', all_varchar = true);

CREATE OR REPLACE TABLE silver.fx_rates AS
SELECT CAST(clean_text(date) AS DATE)                   AS rate_date,
       UPPER(clean_text(currency))                     AS currency,
       TRY_CAST(clean_text(rate_to_usd) AS DECIMAL(12,6)) AS rate_to_usd
FROM bronze.ref_fx_rates;
-- repo: ISO dates written in three ways in MM06 (2026-03-04, 03/04/2026, 04-Mar-26)
CREATE OR REPLACE MACRO to_date_any(x) AS
  COALESCE(TRY_CAST(TRY_STRPTIME(clean_text(x), '%Y-%m-%d') AS DATE),
           TRY_CAST(TRY_STRPTIME(clean_text(x), '%m/%d/%Y') AS DATE),
           TRY_CAST(TRY_STRPTIME(clean_text(x), '%d-%b-%y') AS DATE));

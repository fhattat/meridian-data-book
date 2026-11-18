-- 30_customers.sql
-- One row per SOURCE customer record: Meridian loyalty member, Bazaarly user, Meridian business account.
-- The same person can appear more than once; silver.customer_xref (70_xref.sql) links them by e-mail.
-- Personal data: only email_norm is kept (for matching); names, phones and birth dates stay in bronze.
CREATE OR REPLACE TABLE silver.customers AS
WITH region_of_state AS (
  SELECT DISTINCT UPPER(clean_text(STATE)) AS state_code,
         CASE clean_text(REGION_NAME) WHEN 'Mid-West' THEN 'Midwest' ELSE clean_text(REGION_NAME) END AS region
  FROM bronze.mm_regions
),
members AS (
  SELECT 'MM-M-' || clean_text(m.MEMBER_NO)            AS customer_id,
         'MM'                                          AS source_company,
         'member'                                      AS customer_type,
         clean_text(m.MEMBER_NO)                       AS source_key,
         CASE WHEN clean_text(m.EMAIL) LIKE '%@%' THEN LOWER(TRIM(m.EMAIL)) END AS email_norm,
         UPPER(clean_text(m.STATE))                    AS state_code,
         r.region,
         to_date_any(m.JOIN_DATE)                      AS customer_since,
         COALESCE(clean_text(m.MEMBER_NO) IN (
           SELECT key_value FROM ref_test_records WHERE entity = 'mm_member'), FALSE) AS is_test
  FROM bronze.mm_loyalty_members m
  LEFT JOIN region_of_state r ON r.state_code = UPPER(clean_text(m.STATE))
),
users AS (
  SELECT 'BZ-U-' || clean_text(u.user_id)              AS customer_id,
         'BZ'                                          AS source_company,
         'user'                                        AS customer_type,
         clean_text(u.user_id)                         AS source_key,
         CASE WHEN clean_text(u.email) LIKE '%@%' THEN LOWER(TRIM(u.email)) END AS email_norm,
         a.state_code,
         a.region,
         CAST(CAST(clean_text(u.created_at) AS TIMESTAMPTZ) AS DATE) AS customer_since,
         COALESCE(clean_text(u.user_id) IN (
           SELECT key_value FROM ref_test_records WHERE entity = 'bz_user'), FALSE) AS is_test
  FROM bronze.bz_users u
  LEFT JOIN silver.addresses a ON a.user_id = clean_text(u.user_id) AND a.is_default
),
accounts AS (
  SELECT 'MM-A-' || clean_text(ACCOUNT_ID)             AS customer_id,
         'MM'                                          AS source_company,
         'account'                                     AS customer_type,
         clean_text(ACCOUNT_ID)                        AS source_key,
         CASE WHEN clean_text(CONTACT_EMAIL) LIKE '%@%' THEN LOWER(TRIM(CONTACT_EMAIL)) END AS email_norm,
         UPPER(clean_text(a.STATE))                    AS state_code,
         r.region,
         CAST(NULL AS DATE)                            AS customer_since,
         FALSE                                         AS is_test
  FROM bronze.mm_finance_accounts a
  LEFT JOIN region_of_state r ON r.state_code = UPPER(clean_text(a.STATE))
)
SELECT * FROM members
UNION ALL BY NAME SELECT * FROM users
UNION ALL BY NAME SELECT * FROM accounts;

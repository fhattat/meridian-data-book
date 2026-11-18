-- 10_stores_geo.sql
-- The book shows the stores part (Chapter 9.4, "shortened"); this is the full file.
CREATE OR REPLACE TABLE silver.stores AS
SELECT
  clean_text(STORE_CD)                       AS store_id,
  clean_text(STORE_NAME)                     AS store_name,
  clean_text(CITY)                           AS city,
  UPPER(clean_text(STATE))                   AS state_code,
  CASE clean_text(REGION) WHEN 'Mid-West' THEN 'Midwest' ELSE clean_text(REGION) END AS region,
  CASE clean_text(TIME_ZONE)
    WHEN 'ET' THEN 'America/New_York'  WHEN 'CT' THEN 'America/Chicago'
    WHEN 'MT' THEN 'America/Denver'    WHEN 'PT' THEN 'America/Los_Angeles'
  END                                        AS iana_tz,
  TRY_CAST(clean_text(OPEN_DATE) AS DATE)    AS open_date,
  'MM'                                       AS source_company
FROM bronze.mm_stores;

-- BZ02: states (one row per state / region code)
CREATE OR REPLACE TABLE silver.states AS
SELECT UPPER(clean_text(state_code)) AS state_code,
       clean_text(state_name)        AS state_name,
       clean_text(region)            AS region,        -- US: Census region; elsewhere: Canada, United Kingdom, Europe
       UPPER(clean_text(country))    AS country
FROM bronze.bz_states;

-- BZ02: cities. The header row inside the data is dropped; the state written in three ways
-- ("CA", "Calif.", "California") is mapped to a code with ref/state_aliases.csv.
CREATE OR REPLACE TABLE silver.cities AS
SELECT clean_text(c.city_id)      AS city_id,
       clean_text(c.city_name)    AS city_name,
       a.state_code,
       UPPER(clean_text(c.country)) AS country
FROM bronze.bz_cities c
LEFT JOIN ref_state_aliases a ON a.alias = clean_text(c.state)
WHERE clean_text(c.city_id) <> 'city_id';

-- BZ01: addresses with their city, state, country and region (one row per address)
CREATE OR REPLACE TABLE silver.addresses AS
SELECT clean_text(ad.address_id)  AS address_id,
       clean_text(ad.user_id)     AS user_id,
       clean_text(ad.address_type) AS address_type,
       clean_text(ad.is_default) = '1' AS is_default,
       ci.city_name, ci.state_code, ci.country, st.region
FROM bronze.bz_user_addresses ad
LEFT JOIN silver.cities ci ON ci.city_id = clean_text(ad.city_id)
LEFT JOIN silver.states st ON st.state_code = ci.state_code;

-- 10_dim_store.sql - 48 stores plus one "Bazaarly Online" row, so every sale has a store (Chapter 11.7).
CREATE OR REPLACE TABLE gold.dim_store AS
SELECT sha256(store_id) AS store_key, store_id, store_name, city, state_code, region, iana_tz,
       'store' AS channel, 'MM' AS source_company
FROM silver.stores
UNION ALL
SELECT sha256('BZ-ONLINE'), 'BZ-ONLINE', 'Bazaarly Online', NULL, NULL, NULL, 'UTC', 'online', 'BZ';

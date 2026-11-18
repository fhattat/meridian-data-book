COMMENT ON TABLE meridian.silver.customers IS
  'One row per source customer record (member, user or account). See glossary term: customer.';

ALTER TABLE meridian.silver.customers ALTER COLUMN email_norm
  COMMENT 'Lower-cased, trimmed e-mail; used to match the same person across companies.';

ALTER TABLE meridian.silver.customers SET TAGS ('domain' = 'customer', 'owner' = 'crm_director');
ALTER TABLE meridian.silver.customers ALTER COLUMN email_norm SET TAGS ('pii' = 'direct');

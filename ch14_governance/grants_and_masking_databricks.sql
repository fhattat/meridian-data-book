GRANT USE CATALOG ON CATALOG meridian TO `analysts`;
GRANT USE SCHEMA, SELECT ON SCHEMA meridian.gold TO `analysts`;
GRANT USE SCHEMA ON SCHEMA meridian.gold TO `ai_assistant_sp`;
GRANT SELECT ON TABLE meridian.gold.rag_chunks TO `ai_assistant_sp`;

CREATE OR REPLACE FUNCTION meridian.silver.mask_email(email STRING)
  RETURN CASE WHEN is_account_group_member('pii_readers') THEN email
              ELSE regexp_replace(email, '^[^@]+', '***') END;

ALTER TABLE meridian.silver.customers ALTER COLUMN email_norm SET MASK meridian.silver.mask_email;

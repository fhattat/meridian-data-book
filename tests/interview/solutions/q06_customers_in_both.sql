-- Question 6: how many people are both Meridian members and Bazaarly users?
-- Trap: upper/lower case and spaces in e-mails; test records.
-- Solution: silver.customer_xref is already built on the normalized e-mail (email_norm).
-- Test records are left out with NOT EXISTS (NOT IN can return nothing because of NULL).
SELECT COUNT(DISTINCT x.email_norm) AS people_in_both
FROM silver.customer_xref AS x
WHERE x.mm_member_id IS NOT NULL
  AND x.bz_user_id   IS NOT NULL
  AND NOT EXISTS (
        SELECT 1
        FROM silver.customers AS c
        WHERE c.email_norm = x.email_norm
          AND c.is_test = TRUE
  );

-- Without the xref table, the same question from silver.customers:
-- SELECT COUNT(*) FROM (
--     SELECT lower(trim(email_norm)) AS e
--     FROM silver.customers
--     WHERE is_test = FALSE
--     GROUP BY lower(trim(email_norm))
--     HAVING SUM(CASE WHEN customer_type = 'member' THEN 1 ELSE 0 END) > 0
--        AND SUM(CASE WHEN customer_type = 'user'   THEN 1 ELSE 0 END) > 0
-- ) t;

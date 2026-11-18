-- Question 8: are any POS lines lost between bronze and silver?
-- Trap: test records are flagged with is_test in silver, not deleted, so they are not "lost".
-- In bronze everything is text and may contain spaces; normalize the key as silver does.
-- Solution: line keys in bronze EXCEPT line keys in silver.
SELECT TRIM(b.RECEIPT_NO) AS receipt_no,
       CAST(TRIM(b.LINE_NO) AS INTEGER) AS line_no
FROM bronze.mm_pos_named AS b
WHERE b.rec_type = 'L'
EXCEPT
SELECT p.receipt_no, p.line_no
FROM silver.pos_lines AS p
ORDER BY receipt_no, line_no;
-- If the result is not empty, put each difference in a category: in quarantine (quality.quarantine),
-- a conversion error (type cast), or an unexplained loss? Only the last one is an incident.
-- Check the other direction too: a line in silver but not in bronze is a sign of a double load.

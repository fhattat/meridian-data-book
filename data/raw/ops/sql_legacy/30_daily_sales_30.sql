-- daily sales report for region Northeast
SELECT *
FROM pos_lines l
INNER JOIN products p ON l.PROD_CD = p.PROD_CD
WHERE l.STORE_CD IN (SELECT STORE_CD FROM stores WHERE REGION = 'Northeast')
  AND l.MEMBER_NO <> '999'
  AND l.QTY > 0;

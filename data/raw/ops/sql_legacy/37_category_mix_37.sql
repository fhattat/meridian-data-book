SELECT CASE WHEN CATEGORY_PATH LIKE 'Electronics%' THEN 'ELEC'
            WHEN CATEGORY_PATH LIKE 'Home%' THEN 'HOME'
            ELSE 'OTHER' END AS cat,
       SUM(LINE_AMT * 1.0825) AS sales_with_tax
FROM pos_lines l
INNER JOIN products p ON l.PROD_CD = p.PROD_CD
GROUP BY 1;

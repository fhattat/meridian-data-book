# Meridian ERP - data dictionary (partial, 2019)

Synthetic document for the book. Only the columns below were ever documented; the rest is unknown.

| Table | Column | Meaning |
|---|---|---|
| mm_stores | STORE_CD | Store code, MM-001 ... MM-048 |
| mm_stores | REGION | US Census region of the store (Northeast, Midwest, South, West) |
| mm_stores | TIME_ZONE | ET, CT, MT or PT; POS times are written in this local time |
| mm_products | PROD_CD | Product code, PRD-00001 ... |
| mm_products | CATEGORY_PATH | "Category > Subcategory" |
| mm_products | UNIT_PRICE | List price in USD as text, e.g. "$1,299.00" |
| mm_inventory_monthly | (month columns) | Units on hand at month end, one column per month |

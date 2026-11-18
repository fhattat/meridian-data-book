# Bazaarly event stream - schema (synthetic)

One JSON object per line (JSON Lines), one file per UTC day.

| Field | Meaning |
|---|---|
| event_id | Unique id of the event; the same event can be delivered twice |
| ts | Event time in UTC (until 2026-05-31) |
| event_time | Event time in UTC (from 2026-06-01; replaces ts) |
| user_id | Bazaarly user |
| session_id | App session |
| event_type | page_view, add_to_cart, checkout, purchase |
| product_code | Catalogue id (bz_products.product_code) |

Events can arrive late: an event of day D may be in the file of day D+1.

# Gold model: grain and metric definitions

Used as context in the Chapter 11.8 / 18.5 experiment (`text_to_sql_eval.py --layer gold`) and by
the fan-out agent (Chapter 16.4). Galaxy schema: 8 dimensions, 6 facts. All keys are deterministic
SHA-256 hashes (DuckDB `sha256(x)`, Databricks `sha2(x, 256)`). Dates are integer keys `YYYYMMDD`.

## Facts

| Table | Grain (one row is ...) | Measures | Dimensions |
|---|---|---|---|
| fact_sales | one sales line: a Meridian receipt line or a Bazaarly order item | quantity, amount_usd | date, product, store, customer, seller (BZ), geo (ship/bill), order_flags |
| fact_order_process | one Bazaarly order (accumulating snapshot); shipments rolled up to the order | shipment_count, days_to_delivery, order_total_usd | date x 5 roles (order, invoice, paid, first shipped, delivered), customer, geo, |
| fact_inventory | product x month (periodic snapshot, month-end units) | units | date (month_key), product |
| fact_sales_targets | store x month | target_usd | date (month_key), store |
| fact_campaign_spend | campaign x day | spend_usd, impressions | date, campaign |
| fact_promotion_coverage | campaign x product (factless) | - | campaign, product |

## Dimensions

| Table | One row is ... | Notes |
|---|---|---|
| dim_date | a calendar day | generated from the facts' first and last dates; `year_month` = 'YYYY-MM' |
| dim_product | a master product | Meridian and Bazaarly products matched by UPC or ref/product_mapping.csv; twins removed by survivorship; `category` from Meridian when both exist |
| dim_store | a Meridian store, plus one row `BZ-ONLINE` for Bazaarly | `region` = US Census region; NULL for BZ-ONLINE |
| dim_customer | a customer version (SCD 2) | member `MM-M-`, user `BZ-U-`, account `MM-A-`; `UNKNOWN` for anonymous store receipts; not de-duplicated across companies (see silver.customer_xref) |
| dim_seller | a Bazaarly seller | |
| dim_geo | city x state x country | `region`: Census region in the US, otherwise Canada / United Kingdom / Europe |
| dim_order_flags | channel x order_status x payment_type (junk) | channel code 50 is `UNMAPPED` on purpose |
| dim_campaign | a campaign | |

## Metric definitions (metrics/sales.yaml)

- **net_sales_usd** = `SUM(fact_sales.amount_usd)`. Test records and cancelled or returned
  Bazaarly orders are excluded; Meridian returns are negative lines; shipping and sales tax are
  excluded; non-USD orders use the rate of the order date (New York date), for weekends the last
  business day. Never use the order header total.
- **orders** = `COUNT(DISTINCT order_id)` on fact_sales (never `COUNT(*)`: that counts lines).
- **active_customers** = customers with at least one net sales line in the period; the anonymous
  `UNKNOWN` customer is excluded. Definition owned by the CRM director (draft).

## Rules for queries

- Join facts to facts only through shared dimensions (drill-across), never fact to fact.
- Meridian dates are store-local dates; Bazaarly dates are New York dates of the UTC order time.
- Company: `source_company` = 'MM' (Meridian stores) or 'BZ' (Bazaarly online).
- Region of a sale: Meridian from `dim_store.region`, Bazaarly from the ship-to `dim_geo.region`
  (view `gold.v_fact_sales_region`).

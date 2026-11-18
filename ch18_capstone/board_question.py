import json

ct = json.load(open("data/raw/control_totals.json"))["net_sales_usd"]
expected = {
    company: sum(v for period, v in months.items() if period.startswith("2026-"))
    for company, months in ct.items()
}
expected["TOTAL"] = sum(expected.values())
print(expected)   # compare row by row with the query result

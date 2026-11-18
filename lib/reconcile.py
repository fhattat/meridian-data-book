# lib/reconcile.py
"""Keep the number: protects totals across joins and layer transitions."""
import json

import pandas as pd


class ReconcileError(Exception):
    pass


def safe_left_join(left, right, on, measure, step):
    """Runs a LEFT JOIN; stops if the right side is not unique or the total changes."""
    dup = right[right.duplicated(on, keep=False)]
    if not dup.empty:
        raise ReconcileError(f"{step}: duplicate key in the right table ({len(dup)} rows)\n{dup.head(10)}")
    rows_before, sum_before = len(left), round(left[measure].sum(), 2)
    out = left.merge(right, on=on, how="left", indicator=True)
    rows_after, sum_after = len(out), round(out[measure].sum(), 2)
    if rows_after != rows_before or sum_after != sum_before:
        raise ReconcileError(
            f"{step}: number not kept ({rows_before} → {rows_after} rows, "
            f"{sum_before:,.2f} → {sum_after:,.2f})")
    unmatched = int((out["_merge"] == "left_only").sum())
    print(f"{step}: OK, {rows_before} rows, total {sum_before:,.2f}, unmatched {unmatched}")
    return out.drop(columns="_merge")


def reconcile(df, control_totals_path, step, company=None,
              measure="amount_usd", period_col="period", explained=None,
              tolerance=0.01, raise_on_fail=True) -> dict:
    """Compares the table's monthly totals with the control totals.

    df: period ('YYYY-MM') and the amount column; also source_company when company is not given.
    explained: rows missing from the table for a known reason (e.g. quarantine).
    raise_on_fail: True stops on a difference; False only reports it.
    """
    with open(control_totals_path, encoding="utf-8") as f:
        control_all = json.load(f)["net_sales_usd"]          # {company: {period: amount}}
    companies = [company] if company else sorted(control_all)
    diffs, periods = [], 0
    for c in companies:
        part = df if company else df[df["source_company"] == c]
        report = pd.DataFrame({"control": pd.Series(control_all[c], dtype=float)})
        report["in_table"] = part.groupby(period_col)[measure].sum()
        if explained is not None:
            ex = explained if company else explained[explained["source_company"] == c]
            report["explained"] = ex.groupby(period_col)[measure].sum()
        else:
            report["explained"] = 0.0
        report = report.fillna(0.0)
        report["diff"] = (report["control"] - report["in_table"] - report["explained"]).round(2)
        periods += len(report)
        for period, row in report[report["diff"].abs() > tolerance].iterrows():
            diffs.append({"company": c, "period": period, "diff": float(row["diff"])})
    status = "pass" if not diffs else "fail"
    if diffs and raise_on_fail:
        raise ReconcileError(f"{step}: unexplained difference in {len(diffs)} periods\n{diffs[:10]}")
    print(f"{step}: {status}, {periods} periods, unexplained differences {len(diffs)}")
    return {"check": "reconcile", "step": step, "status": status,
            "periods": periods, "diffs": diffs}

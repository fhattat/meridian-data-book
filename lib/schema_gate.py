# lib/schema_gate.py
def schema_gate(batch_columns: list[str], contract: dict) -> dict:
    """Compares a batch's columns with the contract: pass | pass_with_warning | hold."""
    expected = {c["name"] for c in contract["columns"]}
    required = {c["name"] for c in contract["columns"] if c.get("required", True)}
    got = set(batch_columns)
    missing = sorted(required - got)
    unexpected = sorted(got - expected)
    if missing:
        decision = "hold"
    elif unexpected:
        decision = "pass_with_warning"
    else:
        decision = "pass"
    return {"decision": decision, "missing": missing, "unexpected": unexpected}

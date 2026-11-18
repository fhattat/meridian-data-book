"""Reads architecture.yaml and produces a Mermaid flowchart.
Usage: python architecture_to_mermaid.py architecture.yaml > architecture.mmd
Requires: pip install pyyaml
"""
import sys
import yaml

GROUPS = [("sources", "Sources"), ("layers", "Platform"), ("consumers", "Consumers")]
REQUIRED = ("mode", "schedule", "owner")  # every arrow's contract must have these


def to_mermaid(arch: dict) -> str:
    lines = ["flowchart LR"]
    known = set()
    for key, title in GROUPS:
        lines.append(f'  subgraph {key}["{title}"]')
        for item in arch.get(key, []):
            known.add(item["id"])
            label = item["name"]
            if item.get("datasets"):
                label += "<br/>" + ", ".join(item["datasets"])
            lines.append(f'    {item["id"]}["{label}"]')
        lines.append("  end")
    for flow in arch.get("flows", []):
        for end in (flow["from"], flow["to"]):
            if end not in known:
                raise ValueError(f"Undefined node: {end}")
        note = flow.get("mode", "")
        if flow.get("owner"):
            note = f"{note} / {flow['owner']}" if note else flow["owner"]
        arrow = f'-- "{note}" -->' if note else "-->"
        lines.append(f'  {flow["from"]} {arrow} {flow["to"]}')
    return "\n".join(lines)


def missing_contracts(arch: dict) -> list[str]:
    problems = []
    for flow in arch.get("flows", []):
        missing = [k for k in REQUIRED if not flow.get(k)]
        if missing:
            problems.append(f"{flow['from']} -> {flow['to']}: missing {', '.join(missing)}")
    return problems


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "architecture.yaml"
    with open(path, encoding="utf-8") as f:
        arch = yaml.safe_load(f)
    print(to_mermaid(arch))
    for problem in missing_contracts(arch):
        print(f"WARNING: {problem}", file=sys.stderr)

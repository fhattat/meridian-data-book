# Chapter 17 — Using agents safely and reliably

QR-17 · book repository: https://github.com/fhattat/meridian-data-book

**[BOOK_CODE.md](BOOK_CODE.md)**: every code block of the chapter, in book order, under the book's section headings.

## Run

From the repository root, with `export PYTHONPATH=.` (the Makefile sets it for you):

```bash
python ch17_agent_safety/agent_eval.py   # needs an agent runner, see guardrails.py
```

## Files

- [RULES_abridged.md](RULES_abridged.md)
- [agent_audit_table.sql](agent_audit_table.sql)
- [agent_eval.py](agent_eval.py)
- [eval/scenarios.yaml](eval/scenarios.yaml)
- [guardrails.py](guardrails.py)
- [incident_INC-20270812-01.yaml](incident_INC-20270812-01.yaml)
- [support_assistant_system_prompt.txt](support_assistant_system_prompt.txt)
- [tickets/injection_T-18842.jsonl](tickets/injection_T-18842.jsonl)

All data is synthetic (see the main README).

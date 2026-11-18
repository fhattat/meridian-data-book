# Project context: <project name>

## Purpose
<One paragraph: who it is for and which question it answers.>

## Data and layers
- Catalog / database: <meridian | data/meridian.duckdb>
- Layers: raw, bronze (raw + audit columns), silver (clean), gold (star schema), quality
- Canonical table and column names: <file path>
- Metric definitions: metrics/sales.yaml (the net sales definition lives here)

## Rules
- Do not invent column meanings, code mappings or business rules; if there is no source, write "unknown".
- Take technical facts (row counts, NULL rates) from code that was actually run.
- After every JOIN, check the row count and the total (protect the number).
- rules.yaml, the tests and this file are not changed.
- Deleting, publishing, sending and deploying to production may be proposed, never done.

## Code layout
- Every script: python <script>.py --env local|databricks; with run(**kwargs) -> dict inside
- Shared code: lib/ (io, reconcile, schema_gate, llm)
- Changes are small and cover one topic; each change is explained in one sentence.

## Known traps
- <e.g. channel code 50 is missing from the mapping; such orders are kept as UNMAPPED.>

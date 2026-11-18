# Meridian Data Platform — project context

## What we are building
We combine Meridian Market (48 stores, US) and Bazaarly (online marketplace) data
on Databricks in bronze/silver/gold layers.

## Folders
- data/raw: source files, NEVER modify
- ref/: reference and seed files (code mappings, test records, source guide)
- chXX_*/: chapter scripts (Python, English names)
- tests/: a small-data test for every script

## Rules
- Never write to raw data; output goes only to bronze/silver/gold.
- Never change a failing test; fix the code.
- One change touches one file and at most ~200 lines.
- Do not invent column meanings or code mappings; if the source document does not say, leave it empty and ask.
- Never write personal data columns (email, phone, birth date) to output or logs.

## Known traps
- Meridian POS: ';' delimiter, Windows-1252, store local time.
- Bazaarly: UTC; channel_code meanings are in source_system_guide.pdf.

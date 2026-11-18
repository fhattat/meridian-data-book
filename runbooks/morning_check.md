# runbooks/morning_check.md

## Steps
1. Read the status of the nightly job (incident: log scan). If it has not finished, stop and tell a human.
2. Compare each bronze table's row count with yesterday (quality: volume rules).
   A drop of more than 20%: critical. Profile the source (profile).
3. For sources with a contract, read the schema gate result. 'hold' is critical.
4. Collect the quality results; if anything is critical, look for its cause in incident_log.yaml.
5. Write the report: an evidence query and a proposed next step for every critical finding.
6. Never: re-run, delete, publish to production, send email. Write a draft and leave it to a human.


## Thresholds
| Check                            | Info               | Warning            | Critical                     |
|----------------------------------|--------------------|--------------------|------------------------------|
| Row count (vs. the same weekday last week; replaces "yesterday" in step 2) | within +/- 10% | 10-20% drop | more than 20% drop, or zero |
| Quality rules                    | all pass           | any warning        | critical fail                |
| Freshness (gold last updated)    | before 06:00       | 06:00-07:30        | after 07:30 (SLO breach)     |
| schema_gate                      | pass               | pass_with_warning  | hold                         |
| Log errors                       | timeout fixed on retry | repeated warning | step ending in ERROR       |

## Extra check options (these only)
- channel_breakdown: on a volume drop, break down by channel and source company
- incident_lookup: on a critical log error, run the incident tool with that day's date
- late_step: on a freshness breach, find in the log which step finished late

## Acceptance criteria (before the report goes to a human)
- Every critical finding has an evidence query (evidence_query).
- Every recommendation names the rule or record it is based on (based_on: rule name or INC- id).
- No recommendation contains any of the four actions in step 6.
- If it fails twice, the report is left to a human with an "I'm not sure" note.

## Recipients (drafts go under reports/drafts/, none are sent)
| Domain        | Sub-agent    | Draft recipient            |
|---------------|--------------|----------------------------|
| Store / POS   | store_pos    | Marcus                     |
| Marketplace   | marketplace  | Bazaarly source owner      |
| Customer      | customer     | Priya                      |
| Events        | events       | Sam                        |
| Summary       | Bit (manager) | Deniz                     |
- For every critical finding that affects the dashboard, a separate short note to Marcus (he owns the dashboard).
# runbooks/<job_name>.md

## Purpose
<Who does this job produce a report for, for which decision, and when?>

## Steps (in order)
1. <Fixed check: tool + parameters>
2. <Fixed check>
3. Based on the findings, choose only from the "Extra checks" list (at most 3 rounds).
4. Write the report; put drafts under reports/drafts/.

## Thresholds
| Check | Info | Warning | Critical |
|---|---|---|---|
| <e.g. row count vs. the same weekday last week> | +/- 10% | 10-20% drop | more than 20% drop |

## Extra checks (these only)
- <name>: <when to choose it>

## Never
- Delete, re-run, publish to production, send email.

## Acceptance criteria (before the report goes to a human)
- Every critical finding has an evidence query.
- Every recommendation names the rule or record it is based on.
- No recommendation contains an action from the "Never" list.
- If it fails twice, the report is left to a human with an "I'm not sure" note.

## Recipients
| Domain | Draft recipient |
|---|---|

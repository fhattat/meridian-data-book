# ADR-003: POS data arrives as a daily batch; Bazaarly events are ingested as a stream and processed daily

Status: Accepted
Date: 2027-02-15
Decision owner: Priya (data architect)
Consulted: Deniz (data engineering), Marcus (finance), Sam (AI), Bazaarly product team

## Context
- Store sales arrive every night as a single CSV file.
- Bazaarly web and app events are produced continuously (JSON).
- No business unit gave a concrete answer to "What would you do differently if it were 9:05?"
- The support assistant must see order status with at most one hour of delay.

## Options
1. Everything as a daily batch.
2. End-to-end streaming for events (ingestion + processing + serving).
3. Events are ingested as a stream and written to the lake, processed once a day; order status as an hourly micro-batch.

## Decision
Option 3.

## Rationale
- No event loss, because ingestion never stops.
- No always-on processing infrastructure; lower cost and complexity.
- If a real-time need appears later, a new branch can be fed from the same stream.

## Cost
- Event data in reports is at most one day old.
- Late-arriving events need a next-day correction (Chapter 8).

## When do we revisit?
- When a business unit shows, with a concrete example, that an hour of delay loses money.

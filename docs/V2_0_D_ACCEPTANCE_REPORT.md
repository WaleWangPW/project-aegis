# Project Aegis V2.0-D Acceptance Report

Status: `V2.0-D PASS`

Accepted at: `2026-07-11T17:06:45.211751+08:00`

Acceptance target: `V2.0-D Event Timeline and Scenarios`

## What V2.0-D Proves

`V2.0-D Event Timeline and Scenarios` proves that Project Aegis can maintain
bounded event notes and scenario summaries for a stock.

The accepted path proves:

- Events are scoped to one symbol and market.
- Scenarios must reference event evidence.
- Verified events can support decision context.
- Social/community discussion is context only, not verified fact.
- Event and scenario summaries do not bypass Evidence Gate.

This stage is the local safety container for future online market-intelligence
ingestion. It does not implement live web ingestion yet.

## Evidence

- Command: `.venv/bin/python scripts/validate_v2_0_d_event_timeline.py --run-id v2_0_d_20260711_acceptance`
- Exit code: `0`
- Marker: `data/reports/V2_0_D_EVENT_TIMELINE_PASS.marker`
- Report JSON: `data/reports/v2_0_d_event_timeline_latest.json`
- Report Markdown: `data/reports/v2_0_d_event_timeline_latest.md`
- Isolated run dir: `data/processed/v2_0_d_acceptance/v2_0_d_20260711_acceptance`
- Network used: `false`
- Dashboard Contract changed: `false`
- Production records written: `false`

## Acceptance Checks

- Events present: `PASS`
- Verified event present: `PASS`
- Community context not verified: `PASS`
- Scenario has evidence: `PASS`
- Scenario evidence resolved: `PASS`
- Accepted for decision support: `PASS`
- Does not bypass Evidence Gate: `PASS`
- No broker or real trade: `PASS`

Summary:

- Symbol: `CRCL`
- Market: `US`
- Event count: `2`
- Verified event count: `1`
- Scenario count: `1`
- Accepted for decision support: `true`

## Hashes

- Report JSON SHA256: `1e46b837c94509a274ea14f4457aa03ef3af969e1895204dc912807d2fa9e629`
- Report Markdown SHA256: `105147b6e488d29c599b1e35e3f0c16cc8508526ab52798def7213c77c6169fa`
- Marker SHA256: `7ec39da68c4d9ce8844dd692da33d1040f93cc57dc20e2dc884994d52472108e`
- Timeline JSON SHA256: `b9a465ba9547fc5034948906a9d9885fa59525287b724f8a5703d41ed43e53cc`
- Timeline Markdown SHA256: `c06d64cfec4cd92d99312e0d617f4507302662e017653daf42e92875dc1752e8`

## Safety Boundary

- Read-only event and scenario layer.
- No live web ingestion in this stage.
- No real trade.
- No broker API.
- No account sync.
- No webhook.
- No auto-rebalance.
- No strategy mutation.
- No Dashboard Contract change.
- No production `data/records` mutation.
- Social sentiment is not fact.
- User-submitted external execution facts remain evidence inputs only.

## Next Version Target

After `V2.0-D PASS`, the next product target is `V2.0-E External Source
Registry and Policy Gate`, which should define source permissions before any
live web ingestion is implemented.


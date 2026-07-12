# V2.12-G Acceptance Report

Acceptance target: `V2.12-G H-US User Feedback Intake For Simulation Brief`

Purpose: consume the V2.12-F H/US simulation brief and record user feedback as
evidence-only records. This stage allows watch/ignore/manual external action
notes and screenshot evidence paths, while preventing feedback from becoming
real trades or production records.

## Expected Evidence

- `data/reports/V2_12_G_H_US_FEEDBACK_INTAKE_PASS.marker`
- `data/reports/v2_12_g_h_us_feedback_intake_latest.json`
- `data/reports/v2_12_g_h_us_feedback_intake_latest.md`
- `data/processed/v2_12_g_acceptance/<run_id>/h_us_feedback_records.json`
- `data/processed/v2_12_g_acceptance/<run_id>/h_us_simulation_followup_candidates.json`

## Acceptance Meaning

`V2.12-G PASS` means:

- V2.12-F was used as the source brief.
- User feedback can be accepted for valid H/US simulation brief items.
- `manual_ignore` does not create follow-up candidates.
- Watch/manual external action feedback can create simulation follow-up
  candidates for later paper/review processing.
- Unknown brief items and secret-like text are blocked.
- Screenshots are stored as evidence paths and hashes only.
- Production `Recommendation`, `PaperTrade`, `Review`, and `Memory` records are
  not mutated.

## Boundary

- User-submitted evidence only.
- Simulation-only.
- Manual external execution only.
- No real trade execution.
- No live price.
- No position size.
- No broker API.
- No trading webhook.
- No order placement.
- No production record mutation.
- Dashboard Contract unchanged.

## Result

Latest accepted run:

- `run_id`: `v2_12_g_20260712_acceptance`
- `feedback_count`: `5`
- `accepted_count`: `3`
- `blocked_count`: `2`
- `simulation_followup_count`: `2`
- `network_used`: `false`
- `production_records_written`: `false`
- `dashboard_contract_changed`: `false`

## Next

`V2.12-H H-US Feedback To Paper Simulation Review Queue`: convert accepted
V2.12-G simulation follow-up candidates into a review queue that still requires
user-supplied price/date evidence before any virtual paper trade is created.

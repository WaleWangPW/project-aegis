# V2.12-F Acceptance Report

Acceptance target: `V2.12-F H-US Current Usable Simulation Brief Refresh`

Purpose: consume the V2.12-E H/US Suggestion Gate report and generate a
user-readable H/US simulation brief. This stage makes the current H/US
simulation candidates readable, while preserving every no-real-trade boundary.

## Expected Evidence

- `data/reports/V2_12_F_H_US_CURRENT_SIMULATION_BRIEF_PASS.marker`
- `data/reports/v2_12_f_h_us_current_simulation_brief_latest.json`
- `data/reports/v2_12_f_h_us_current_simulation_brief_latest.md`
- `data/processed/v2_12_f_acceptance/<run_id>/h_us_current_simulation_brief.json`
- `data/processed/v2_12_f_acceptance/<run_id>/h_us_current_simulation_brief.md`

## Acceptance Meaning

`V2.12-F PASS` means:

- V2.12-E was used as the source evidence.
- The brief contains H and U.S. simulation candidates.
- The brief is readable by the user in Markdown.
- Every item remains simulation-only and manual-external-execution-only.
- Production `Recommendation`, `PaperTrade`, `Review`, and `Memory` records were
  not mutated.
- No network fetch occurred in this stage.

## Boundary

- Simulation-only.
- Not real trade advice.
- Preliminary sample only.
- No live price.
- No position size.
- No broker API.
- No trading webhook.
- No order placement.
- No production record mutation.
- Dashboard Contract unchanged.

## Result

Latest accepted run:

- `run_id`: `v2_12_f_20260712_acceptance`
- `candidate_count`: `2`
- `blocked_count`: `0`
- `candidate_markets`: `H`, `US`
- `network_used`: `false`
- `production_records_written`: `false`
- `dashboard_contract_changed`: `false`

## Next

`V2.12-G H-US User Feedback Intake For Simulation Brief`: allow the user to
record watch/ignore/manual external action notes and screenshot/text evidence
for the V2.12-F H/US simulation brief, without writing real trading records.

# V2.12-D Acceptance Report

Acceptance target: `V2.12-D H-US Historical Sandbox Candidate Refresh Dry Run`

Purpose: consume the V2.12-C run-specific normalized H/US cache samples and
turn them into preliminary historical sandbox candidates and cases. This stage
proves the cache-to-sandbox wiring. It does not prove a production strategy and
does not generate user-facing suggestions.

## Expected Evidence

- `data/reports/V2_12_D_H_US_HISTORICAL_SANDBOX_CANDIDATE_REFRESH_PASS.marker`
- `data/reports/v2_12_d_h_us_historical_sandbox_candidate_refresh_latest.json`
- `data/reports/v2_12_d_h_us_historical_sandbox_candidate_refresh_latest.md`
- `data/processed/v2_12_d_acceptance/<run_id>/h_us_historical_sandbox_cases.jsonl`
- `data/processed/v2_12_d_acceptance/<run_id>/h_us_sandbox_strategy_candidates.json`

## Acceptance Meaning

`V2.12-D PASS` means:

- V2.12-C normalized cache samples can be converted into `HistoricalStrategyCase`
  inputs.
- H and U.S. preliminary sandbox candidates can be evaluated by the existing
  strategy sandbox.
- The result is preliminary simulation evidence only.
- Suggestion Gate remains required before any user-facing candidate or brief.

## Boundary

- Preliminary historical sandbox input only.
- Sample size is intentionally small.
- Not production strategy evidence.
- No user-facing suggestion allowed.
- No network fetch in this stage.
- No production cache mutation.
- No production provider config mutation.
- No production Recommendation/PaperTrade/Review/Memory mutation.
- No real trade.
- No broker API.
- No trading webhook.
- No order placement.
- Dashboard Contract unchanged.

## Next

`V2.12-E H-US Suggestion Gate Refresh From Sandbox Evidence`: route the
preliminary H/US sandbox evidence through the existing Suggestion Gate, keeping
sample-size warnings and manual-execution boundaries visible.

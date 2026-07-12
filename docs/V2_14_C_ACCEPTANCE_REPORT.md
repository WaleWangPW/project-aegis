# V2.14-C Refreshed Candidate Historical Sandbox

## Status

`PASS`

V2.14-C consumes the V2.14-B refreshed candidate pool and evaluates available
A/H historical evidence. It does not fabricate missing data: candidates without
historical coverage are explicitly listed as missing coverage and cannot be
treated as passes.

This stage is historical sandbox evidence only. It is not a user-facing
suggestion; Suggestion Gate remains required.

## Evidence

- Command: `python3 scripts/validate_v2_14_c_refreshed_candidate_historical_sandbox.py --run-id v2_14_c_20260712_acceptance`
- Exit code: `0`
- Report JSON: `data/reports/v2_14_c_refreshed_candidate_historical_sandbox_latest.json`
- Report MD: `data/reports/v2_14_c_refreshed_candidate_historical_sandbox_latest.md`
- Marker: `data/reports/V2_14_C_REFRESHED_CANDIDATE_HISTORICAL_SANDBOX_PASS.marker`
- Sandbox JSON: `data/processed/v2_14_c_acceptance/v2_14_c_20260712_acceptance/refreshed_candidate_historical_sandbox.json`
- Sandbox MD: `data/processed/v2_14_c_acceptance/v2_14_c_20260712_acceptance/refreshed_candidate_historical_sandbox.md`
- Historical cases JSONL: `data/processed/v2_14_c_acceptance/v2_14_c_20260712_acceptance/refreshed_candidate_historical_cases.jsonl`

## Hashes

- Report JSON SHA256: `a0f866be5959c510534626bfffe1559d7f982227eb325fad293dd8e367871376`
- Report MD SHA256: `a7412a4a2e242e53f2f19669693510f350518033c4dd6ed92b05cbd792ff55f0`
- Marker SHA256: `4fa9e7de86cdbb764af1edbc800f3cb82dc089994f38c7df476291d1c974dc95`
- Sandbox JSON SHA256: `a0f866be5959c510534626bfffe1559d7f982227eb325fad293dd8e367871376`
- Sandbox MD SHA256: `a7412a4a2e242e53f2f19669693510f350518033c4dd6ed92b05cbd792ff55f0`
- Historical cases JSONL SHA256: `17b0cd931e8e4cb3ebf1bd9a694052d20e08ffcd168318f69f7cb1b2f11d0e56`

## Result

- Refreshed candidate count: `6`
- Covered candidate count: `3`
- Missing coverage count: `3`
- Historical case count: `3`
- Strategy pass count: `1`
- Strategy fail count: `1`
- Sandbox passed strategies: `strategy_h_low_vol_dividend`
- Sandbox failed strategies: `strategy_a_low_vol_dividend_defensive`
- Covered candidates: `600519.SH`, `600036.SH`, `00700.HK`
- Missing coverage candidates: `601398.SH`, `00005.HK`, `00941.HK`
- User-facing suggestion allowed: `false`
- Next stage: `V2.14-D Refreshed Candidate Suggestion Gate`

## Tests

- Unit tests: `./.venv/bin/pytest tests/test_refreshed_candidate_historical_sandbox_v2_14_c.py -q`
- Unit result: `6 passed`
- Adjacent tests: `./.venv/bin/pytest tests/test_candidate_pool_live_refresh_v2_14_b.py tests/test_refreshed_candidate_historical_sandbox_v2_14_c.py -q`
- Adjacent result: `13 passed`

## Safety Boundary

- `network_used=false`
- `not_user_facing_suggestion=true`
- `suggestion_gate_required=true`
- `coverage_gap_visible=true`
- `production_records_written=false`
- `production_cache_mutated=false`
- `production_provider_config_mutated=false`
- `dashboard_contract_changed=false`
- `no_secret_values_stored=true`
- `request_urls_not_stored=true`
- `raw_payloads_not_stored=true`
- `no_real_trade=true`
- `no_broker_api=true`
- `no_webhook=true`
- `no_order_placement=true`
- `no_position_size=true`
- `no_live_order_signal=true`

## Next

`V2.14-D Refreshed Candidate Suggestion Gate` should consume the V2.14-C
sandbox result. Only sandbox-passed evidence may be considered. Missing
coverage candidates must remain blocked until additional historical evidence is
available.

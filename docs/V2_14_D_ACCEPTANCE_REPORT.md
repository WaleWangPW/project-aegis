# V2.14-D Refreshed Candidate Suggestion Gate

## Status

`PASS`

V2.14-D consumes the V2.14-C refreshed-candidate historical sandbox evidence and
routes it through Suggestion Gate. Only sandbox-passed candidates with
historical evidence can become simulation-only suggestion drafts.

This stage is still not real trading. It creates no live price, no position
size, no broker API, no webhook, no order, and no production records.

## Evidence

- Command: `python3 scripts/validate_v2_14_d_refreshed_candidate_suggestion_gate.py --run-id v2_14_d_20260712_acceptance`
- Exit code: `0`
- Report JSON: `data/reports/v2_14_d_refreshed_candidate_suggestion_gate_latest.json`
- Report MD: `data/reports/v2_14_d_refreshed_candidate_suggestion_gate_latest.md`
- Marker: `data/reports/V2_14_D_REFRESHED_CANDIDATE_SUGGESTION_GATE_PASS.marker`
- Gate JSON: `data/processed/v2_14_d_acceptance/v2_14_d_20260712_acceptance/refreshed_candidate_suggestion_gate.json`
- Gate MD: `data/processed/v2_14_d_acceptance/v2_14_d_20260712_acceptance/refreshed_candidate_suggestion_gate.md`
- Suggestions JSON: `data/processed/v2_14_d_acceptance/v2_14_d_20260712_acceptance/refreshed_candidate_suggestion_drafts.json`

## Hashes

- Report JSON SHA256: `c0fadcfc4776eee5e8d083f2661c1f795b0143d772b88055ae0ad4b45ba37f1c`
- Report MD SHA256: `92d444ad7a1c39f7e417dfaae006a819e850c03221ff37da9d822b6536ddd33c`
- Marker SHA256: `f251ff8fb368e4a02fd23743e91896e13204b3edf76f6a765250eed2a5ecf8e1`
- Gate JSON SHA256: `c0fadcfc4776eee5e8d083f2661c1f795b0143d772b88055ae0ad4b45ba37f1c`
- Gate MD SHA256: `92d444ad7a1c39f7e417dfaae006a819e850c03221ff37da9d822b6536ddd33c`
- Suggestions JSON SHA256: `daf7ed387c55183dd926d5f3e02eedcb3ee34c70564b9e8b71a0b0003140872d`

## Result

- Opportunity count: `6`
- Draft count: `6`
- Allowed count: `1`
- Blocked count: `5`
- Allowed symbols: `00700.HK`
- Blocked symbols: `00005.HK`, `00941.HK`, `600036.SH`, `600519.SH`, `601398.SH`
- Simulation suggestion available: `true`
- Real trade allowed: `false`
- Next stage: `V2.14-E Current Usable Simulation Suggestion Brief`

## Tests

- Unit tests: `./.venv/bin/pytest tests/test_refreshed_candidate_suggestion_gate_v2_14_d.py -q`
- Unit result: `6 passed`
- Adjacent tests: `./.venv/bin/pytest tests/test_refreshed_candidate_historical_sandbox_v2_14_c.py tests/test_refreshed_candidate_suggestion_gate_v2_14_d.py -q`
- Adjacent result: `12 passed`

## Safety Boundary

- `network_used=false`
- `simulation_only=true`
- `manual_external_execution_only=true`
- `not_real_trade_advice=true`
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

`V2.14-E Current Usable Simulation Suggestion Brief` should convert the single
allowed V2.14-D draft into a concise user-readable brief. It must keep the same
simulation-only, manual-external-execution boundary and keep all blocked
symbols visible.

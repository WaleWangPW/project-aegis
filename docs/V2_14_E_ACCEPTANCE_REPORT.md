# V2.14-E Current Usable Simulation Suggestion Brief

## Status

`PASS`

V2.14-E consumes the V2.14-D refreshed-candidate Suggestion Gate output and
turns it into a user-readable simulation brief. It exposes the single allowed
simulation candidate and keeps all blocked symbols visible.

This is not real trading. The brief contains no live price, no position size,
no broker API, no webhook, no order, and no production record mutation.

## Evidence

- Command: `python3 scripts/validate_v2_14_e_refreshed_candidate_simulation_brief.py --run-id v2_14_e_20260712_acceptance`
- Exit code: `0`
- Report JSON: `data/reports/v2_14_e_refreshed_candidate_simulation_brief_latest.json`
- Report MD: `data/reports/v2_14_e_refreshed_candidate_simulation_brief_latest.md`
- Marker: `data/reports/V2_14_E_REFRESHED_CANDIDATE_SIMULATION_BRIEF_PASS.marker`
- Brief JSON: `data/processed/v2_14_e_acceptance/v2_14_e_20260712_acceptance/refreshed_candidate_current_simulation_brief.json`
- Brief MD: `data/processed/v2_14_e_acceptance/v2_14_e_20260712_acceptance/refreshed_candidate_current_simulation_brief.md`

## Hashes

- Report JSON SHA256: `9d4a3972796d9061f804058f5b66161d24a412640192ccdba049c5839d5be5e0`
- Report MD SHA256: `d99a8654db50842f31653b456cb487cc2a75c9ac3908f59c240a60c49b3b9a63`
- Marker SHA256: `d0d1ca37edf5ce8513570c0ac86fe91cfd9d5d2becc7793e2add27b0c4032576`
- Brief JSON SHA256: `9d4a3972796d9061f804058f5b66161d24a412640192ccdba049c5839d5be5e0`
- Brief MD SHA256: `d99a8654db50842f31653b456cb487cc2a75c9ac3908f59c240a60c49b3b9a63`

## Result

- Candidate count: `1`
- Candidate symbols: `00700.HK`
- Blocked count: `5`
- Blocked symbols: `00005.HK`, `00941.HK`, `600036.SH`, `600519.SH`, `601398.SH`
- Simulation suggestion available: `true`
- Real trade allowed: `false`
- Next stage: `V2.14-F User Feedback Intake For Refreshed Simulation Brief`

## Tests

- Unit tests: `./.venv/bin/pytest tests/test_refreshed_candidate_simulation_brief_v2_14_e.py -q`
- Unit result: `6 passed`
- Adjacent tests: `./.venv/bin/pytest tests/test_refreshed_candidate_suggestion_gate_v2_14_d.py tests/test_refreshed_candidate_simulation_brief_v2_14_e.py -q`
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
- `no_live_price=true`
- `no_position_size=true`
- `no_real_trade=true`
- `no_broker_api=true`
- `no_webhook=true`
- `no_order_placement=true`
- `no_live_order_signal=true`

## Current User-Facing Brief

- Current simulation candidate: `00700.HK`
- User action: add to simulation watchlist only; verify current price, news,
  announcements, holdings conflict, and personal risk budget externally.
- User feedback path: if the user acts manually elsewhere, return screenshot,
  typed price/date, or text note to Aegis for review evidence.
- Blocked paths remain blocked and must not be used as current simulation
  candidates.

## Next

`V2.14-F User Feedback Intake For Refreshed Simulation Brief` should accept
watch/ignore/manual-external notes and optional user-supplied evidence for
`00700.HK`, while continuing to block real trading, broker/webhook integration,
live price, order placement, and position sizing.

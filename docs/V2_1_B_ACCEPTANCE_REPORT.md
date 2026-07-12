# Project Aegis V2.1-B Acceptance Report

Status: `V2.1-B PASS`

Date: `2026-07-11`

Acceptance target: `V2.1-B Strategy Candidate Library`

## What V2.1-B Proves

`V2.1-B Strategy Candidate Library` proves that Project Aegis can persist
explicit strategy candidates and reload/filter them for repeatable sandbox
work across A-share, Hong Kong, and U.S. markets.

This is not an optimizer. It does not mutate strategies automatically and does
not produce trades.

## Evidence

Validation command:

```bash
.venv/bin/python scripts/validate_v2_1_b_strategy_candidate_library.py --run-id v2_1_b_20260711_acceptance
```

Exit code: `0`

PASS marker:

- `data/reports/V2_1_B_STRATEGY_CANDIDATE_LIBRARY_PASS.marker`

Reports:

- `data/reports/v2_1_b_strategy_candidate_library_latest.json`
- `data/reports/v2_1_b_strategy_candidate_library_latest.md`

Run artifact:

- `data/processed/v2_1_b_acceptance/v2_1_b_20260711_acceptance/strategy_candidate_library.json`

Hashes:

- `strategy_candidate_library.json`: `dbdfb2ed23f7b38050da2b9541f19f2f6bc4eef76b8e9b83f9751a4cd26c1ee3`
- `report_json`: `eaef97427247c97fcc8f6600cbef1e4b09affdd569f75522ad8b7369497c7423`
- `report_md`: `68ec8fba35fb7e9e184bf43ec6a0c31e234e22a2ee82c7b6db24fbafed7b4198`

## Result Summary

- Candidate count: `4`
- A-share candidates: `value_quality_defensive_a`
- Hong Kong candidates: `low_volatility_dividend_h`
- U.S. candidates: `risk_adjusted_momentum_us`, `portfolio_risk_veto_overlay`
- Duplicate strategy IDs are rejected.
- Strategy filters work by market and factor family.

## Safety Boundaries

Confirmed:

- `simulation_only=true`
- `network_used=false`
- `production_records_written=false`
- `dashboard_contract_changed=false`
- `no_real_trade=true`
- `no_broker_api=true`
- `no_webhook=true`
- `no_secret_storage=true`
- `no_strategy_auto_mutation=true`
- `suggestion_gate_still_required=true`

## Regression Evidence

Targeted tests:

```bash
.venv/bin/python -m pytest tests/test_strategy_candidate_library_v2_1_b.py tests/test_strategy_sandbox_v2_1_a.py -q
```

Result: `8 passed in 0.09s`

## Next Target

After `V2.1-B PASS`, the next target was `V2.1-C Suggestion Gate`, now also
accepted by `docs/V2_1_C_ACCEPTANCE_REPORT.md`.

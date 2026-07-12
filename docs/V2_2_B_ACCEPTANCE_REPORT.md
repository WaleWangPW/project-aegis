# Project Aegis V2.2-B Acceptance Report

Status: `V2.2-B PASS`

Date: `2026-07-11`

Acceptance target: `V2.2-B API-backed Research Fetch Dry Run`

## What V2.2-B Proves

`V2.2-B` proves that Project Aegis can run a bounded API-backed research fetch
dry-run against an approved connector while keeping API key values, request
headers, and raw response bytes out of persisted artifacts.

This is not broker access, not a trading webhook, and not real trading.

## Evidence

Validation command:

```bash
.venv/bin/python scripts/validate_v2_2_b_api_backed_research_fetch.py --run-id v2_2_b_20260711_acceptance_rerun
```

Exit code: `0`

PASS marker:

- `data/reports/V2_2_B_API_BACKED_RESEARCH_FETCH_PASS.marker`

Reports:

- `data/reports/v2_2_b_api_backed_research_fetch_latest.json`
- `data/reports/v2_2_b_api_backed_research_fetch_latest.md`

Run artifact:

- `data/processed/v2_2_b_acceptance/v2_2_b_20260711_acceptance_rerun/api_fetch_item.json`

Hashes:

- `api_fetch_item.json`: `a8e976b4ba2dd211cec9eedeed8b633fb9c9b65944d8a2881e5b2a70f46c2d00`
- `report_json`: `238633875a71f08763fc01f01becdd92b20fd8d8e8a3e3c31d22effd03582e95`
- `report_md`: `cbff13b03fb5db7466f93f6b5b40cc7f19758a8fa6efcec59acd8cd79756fdfd`

## Result Summary

- Connector: `api_user_research_approved_env`
- Endpoint: `/strategy-notes`
- Status code: `200`
- Auth env var name recorded: `AEGIS_RESEARCH_API_KEY`
- API key value serialized: `false`
- Raw bytes stored: `false`
- Request headers stored: `false`
- Broker API denied: `true`

## Safety Boundaries

Confirmed:

- `network_used=false` in acceptance fixture mode
- `production_records_written=false`
- `dashboard_contract_changed=false`
- `api_key_value_not_stored=true`
- `env_var_names_only=true`
- `request_headers_not_stored=true`
- `raw_bytes_not_stored=true`
- `no_cookie_access=true`
- `no_paywall_bypass=true`
- `no_real_trade=true`
- `no_broker_api=true`
- `no_trading_webhook=true`
- `no_strategy_auto_mutation=true`

## Regression Evidence

Targeted tests:

```bash
.venv/bin/python -m pytest tests/test_api_backed_research_fetch_v2_2_b.py -q
```

Result: `5 passed in 0.09s`

Related regression:

```bash
.venv/bin/python -m pytest tests/test_api_backed_research_fetch_v2_2_b.py tests/test_external_api_research_ingestion_v2_2_a.py tests/test_suggestion_gate_v2_1_c.py tests/test_strategy_candidate_library_v2_1_b.py tests/test_strategy_sandbox_v2_1_a.py tests/test_official_source_fetcher_v2_0_f.py tests/test_external_source_policy_v2_0_e.py tests/test_event_timeline_v2_0_d.py tests/test_research_workspace_v2_0_c.py tests/test_portfolio_aware_brief_v2_0_b.py tests/test_portfolio_foundation_v2_0_a.py tests/test_review_system_v1_5.py tests/test_validate_v1_0_single_cycle.py tests/test_run_backtest.py tests/test_backtest_metrics.py tests/test_time_travel_no_future_data.py -q
```

Result: `81 passed in 0.74s`

## Next Target

After `V2.2-B PASS`, `V2.2-C API Research To Sandbox Candidate Bridge` was
also accepted by `docs/V2_2_C_ACCEPTANCE_REPORT.md`.

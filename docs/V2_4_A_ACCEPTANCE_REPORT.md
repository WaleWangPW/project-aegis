# Project Aegis V2.4-A Acceptance Report

Status: `V2.4-A PASS`

Date: `2026-07-11`

Acceptance target: `V2.4-A Strategy Research Source Catalog`

## What V2.4-A Proves

`V2.4-A` proves that Project Aegis now has a canonical strategy research source
catalog for A-shares, Hong Kong equities, and U.S./global equities.

The catalog is not a strategy engine and does not produce user-facing
suggestions. It stores summary-only metadata that can seed later sandbox
hypotheses.

## Evidence

Validation command:

```bash
.venv/bin/python scripts/validate_v2_4_a_strategy_research_source_catalog.py --run-id v2_4_a_20260711_acceptance_final
```

Exit code: `0`

PASS marker:

- `data/reports/V2_4_A_STRATEGY_RESEARCH_SOURCE_CATALOG_PASS.marker`

Reports:

- `data/reports/v2_4_a_strategy_research_source_catalog_latest.json`
- `data/reports/v2_4_a_strategy_research_source_catalog_latest.md`

Run artifacts:

- `aegis/strategy/research_source_catalog.py`
- `scripts/validate_v2_4_a_strategy_research_source_catalog.py`
- `tests/test_strategy_research_source_catalog_v2_4_a.py`
- `data/processed/v2_4_a_acceptance/v2_4_a_20260711_acceptance_final/strategy_research_source_catalog_corpus.json`

Hashes:

- `aegis/strategy/research_source_catalog.py`: `6e787725014387b9121039e3bdb176ff425cf635665b1a0426deb6200c302c25`
- `scripts/validate_v2_4_a_strategy_research_source_catalog.py`: `a2f1a52d5d76cb6a7a327c0a111bf53548dba89b1cb33439ab6126480c1c2938`
- `tests/test_strategy_research_source_catalog_v2_4_a.py`: `a247176566af6a2ab979e6cdc3c7fec85583c362f7fb3a7a884b21d070724b18`
- `strategy_research_source_catalog_corpus.json`: `404624543331f04584e5ff68bde5a60f87b05b6632f30693d8a6d8203c9c3cc4`
- `report_json`: `dd0a65538a0c5fdbe8e18e2b72eaa88c95dc28c33ba70e3a6137d8cc8a7b0f7d`
- `report_md`: `eb396abb5e05686a3f3e0a9adb414b16374b7441ff59c4d487448fc11af484d8`

## Result Summary

- Record count: `12`
- Market coverage: `A=4`, `H=2`, `US=6`, `GLOBAL=6`
- Strategy family coverage:
  - `value=10`
  - `quality=9`
  - `momentum=7`
  - `low_volatility=8`
  - `dividend=6`
  - `size=6`
  - `multi_factor=7`
  - `risk_overlay=3`
- Publisher coverage:
  - `S&P Dow Jones Indices`
  - `MSCI`
  - `Hang Seng Indexes`
  - `Fama and French`
  - `Kenneth R. French Data Library`
  - `Research Affiliates`
  - `AQR / Financial Analysts Journal`
  - `PanAgora / CAIA`

## Safety Boundaries

Confirmed:

- `summary_only=true`
- `raw_text_not_stored=true`
- `requires_sandbox_before_suggestion=true`
- `network_used=false` in acceptance
- `production_records_written=false`
- `dashboard_contract_changed=false`
- `no_real_trade=true`
- `no_broker_api=true`
- `no_trading_webhook=true`
- `no_strategy_auto_mutation=true`

## Regression Evidence

Targeted tests:

```bash
.venv/bin/python -m pytest tests/test_strategy_research_source_catalog_v2_4_a.py -q
```

Result: `5 passed in 0.08s`

Related regression:

```bash
.venv/bin/python -m pytest tests/test_strategy_research_source_catalog_v2_4_a.py tests/test_real_user_api_dry_run_v2_3_b.py tests/test_api_configuration_handoff_v2_3_a.py tests/test_api_research_bridge_v2_2_c.py tests/test_api_backed_research_fetch_v2_2_b.py tests/test_external_api_research_ingestion_v2_2_a.py tests/test_suggestion_gate_v2_1_c.py tests/test_strategy_candidate_library_v2_1_b.py tests/test_strategy_sandbox_v2_1_a.py tests/test_official_source_fetcher_v2_0_f.py tests/test_external_source_policy_v2_0_e.py tests/test_event_timeline_v2_0_d.py tests/test_research_workspace_v2_0_c.py tests/test_portfolio_aware_brief_v2_0_b.py tests/test_portfolio_foundation_v2_0_a.py tests/test_review_system_v1_5.py tests/test_validate_v1_0_single_cycle.py tests/test_run_backtest.py tests/test_backtest_metrics.py tests/test_time_travel_no_future_data.py -q
```

Result: `95 passed in 0.86s`

## Next Target

After `V2.4-A PASS`, the next no-secret target is
`V2.4-B Strategy Research To Sandbox Hypothesis Queue`.

`V2.3-C Live API Dry Run After User Provides Metadata` remains pending until
the user provides non-secret connector metadata and sets the required local
environment variable outside the repo/Vault.

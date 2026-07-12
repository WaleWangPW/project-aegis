# V2.13-F Finnhub Quote Context Historical Case Assembly Acceptance Report

Status: `PASS`

Date: `2026-07-12`

## Result

Finnhub quote context historical case assembly passed. The stage connected the
V2.13-E `AAPL.US` sandbox candidate binding to existing V2.12-C normalized
historical daily bars and assembled rolling historical cases.

- Candidate packet count: `1`
- Symbol: `AAPL.US`
- Historical case count: `8`
- Sandbox evaluation run: `false`
- Sandbox evaluation required: `true`
- Suggestion Gate required: `true`
- User-facing suggestion allowed: `false`
- Network used in this stage: `false`

## Evidence

- Command: `python3 scripts/validate_v2_13_f_finnhub_quote_historical_case_assembly.py --run-id v2_13_f_20260712_acceptance`
- Exit code: `0`
- Report JSON: `data/reports/v2_13_f_finnhub_quote_historical_case_assembly_latest.json`
- Report MD: `data/reports/v2_13_f_finnhub_quote_historical_case_assembly_latest.md`
- Marker: `data/reports/V2_13_F_FINNHUB_QUOTE_HISTORICAL_CASE_ASSEMBLY_PASS.marker`
- Assembly JSON: `data/processed/v2_13_f_acceptance/v2_13_f_20260712_acceptance/finnhub_quote_historical_case_assembly.json`
- Cases JSONL: `data/processed/v2_13_f_acceptance/v2_13_f_20260712_acceptance/finnhub_quote_historical_cases.jsonl`
- Candidates JSON: `data/processed/v2_13_f_acceptance/v2_13_f_20260712_acceptance/finnhub_quote_historical_case_candidates.json`
- Source binding report: `data/reports/v2_13_e_finnhub_quote_sandbox_binding_latest.json`
- Source cache report: `data/reports/v2_12_c_h_us_historical_cache_readiness_latest.json`
- Adjacent tests: `./.venv/bin/pytest tests/test_finnhub_free_probe_v2_13_a.py tests/test_finnhub_metadata_activation_v2_13_b.py tests/test_finnhub_quote_cache_readiness_v2_13_c.py tests/test_finnhub_quote_research_context_v2_13_d.py tests/test_finnhub_quote_sandbox_binding_v2_13_e.py tests/test_finnhub_quote_historical_case_assembly_v2_13_f.py -q`
- Adjacent test result: `40 passed`

## Acceptance Summary

- `overall_status`: `PASS`
- `historical_case_count`: `8`
- `sandbox_evaluation_run`: `false`
- `sandbox_evaluation_required`: `true`
- `suggestion_gate_required`: `true`
- `user_facing_suggestion_allowed`: `false`
- `network_used`: `false`
- `all_artifacts_verified`: `true`

## Safety

- This stage assembles historical cases only.
- No sandbox evaluation result is claimed.
- No user-facing suggestion is generated.
- No production records were written.
- No production cache was mutated.
- No production provider config was mutated.
- No Dashboard Contract change.
- No token values stored.
- No request URL stored.
- No raw payload stored.
- No real trade.
- No broker API.
- No trading webhook.
- No order placement.
- No position size.
- No live order signal.

## Next Stage

`V2.13-G Finnhub Quote Context Sandbox Evaluation`

The next external-data stage may run the assembled `AAPL.US` historical cases
through the historical sandbox. It still must not generate user-facing
suggestions until sandbox evaluation, Suggestion Gate, and risk checks pass.

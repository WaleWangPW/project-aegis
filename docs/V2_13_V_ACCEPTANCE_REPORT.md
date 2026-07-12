# V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation

Status: PASS

## Scope

V2.13-V consumes the 81 rolling historical cases from V2.13-U and evaluates
the `CRCL.US`, `MSFT.US`, and `NVDA.US` Finnhub quote-context sandbox
candidates.

This stage is evaluation only. It does not run Suggestion Gate, does not
produce user-facing suggestions, and does not turn failed sandbox results into
actionable advice.

## Evidence

- Command: `python3 scripts/validate_v2_13_v_finnhub_quote_multi_symbol_sandbox_evaluation.py --run-id v2_13_v_20260712_acceptance`
- Exit code: `0`
- Report JSON: `data/reports/v2_13_v_finnhub_quote_multi_symbol_sandbox_evaluation_latest.json`
- Report MD: `data/reports/v2_13_v_finnhub_quote_multi_symbol_sandbox_evaluation_latest.md`
- Marker: `data/reports/V2_13_V_FINNHUB_QUOTE_MULTI_SYMBOL_SANDBOX_EVALUATION_PASS.marker`
- Sandbox JSON: `data/processed/v2_13_v_acceptance/v2_13_v_20260712_acceptance/finnhub_quote_multi_symbol_sandbox_evaluation.json`
- Results JSON: `data/processed/v2_13_v_acceptance/v2_13_v_20260712_acceptance/finnhub_quote_multi_symbol_sandbox_results.json`
- Source report: `data/reports/v2_13_u_finnhub_quote_multi_symbol_historical_case_assembly_latest.json`
- Unit tests: `./.venv/bin/pytest tests/test_finnhub_quote_multi_symbol_sandbox_evaluation_v2_13_v.py -q`
- Adjacent tests: `./.venv/bin/pytest tests/test_finnhub_free_probe_v2_13_a.py ... tests/test_finnhub_quote_multi_symbol_sandbox_evaluation_v2_13_v.py -q`

## Result

- Candidate count: `3`
- Historical case count: `81`
- Strategy pass count: `0`
- Strategy fail count: `3`
- Passing strategies: none
- Failing strategies:
  - `strategy_crcl_us_finnhub_multi_quote_context_probe`
  - `strategy_msft_us_finnhub_multi_quote_context_probe`
  - `strategy_nvda_us_finnhub_multi_quote_context_probe`
- Blocked symbols: `CRCL.US`, `MSFT.US`, `NVDA.US`
- Suggestion Gate ready: `false`
- User-facing suggestion allowed: `false`
- Next stage: `V2.13-W Finnhub Quote Multi-Symbol Sandbox Result Brief`

## Hashes

- Report JSON SHA256: `ef1aca5555f11bec8ea50cc2959e3290bfb70e2b07680cb553db2c0703418272`
- Marker SHA256: `47fa7db915b95a6a8d7f98e809220e2f8c707c6e7019c444d2d9f0f5a292911a`
- Results JSON SHA256: `d408d03ca60daee195339e0c69f3e9f2cb17128f68d88c5eef149c3a1a12d47e`

## Tests

- `./.venv/bin/pytest tests/test_finnhub_quote_multi_symbol_sandbox_evaluation_v2_13_v.py -q`
  - Result: `7 passed`
- Adjacent Finnhub V2.13 A-V tests
  - Result: `130 passed`

## Interpretation

The stage passed because the evaluation completed with evidence. The strategies
did not pass. Therefore these three multi-symbol candidates must not be routed
to Suggestion Gate as allowed opportunities.

## Safety

- Sandbox evaluation only.
- Failed sandbox results are not promoted to suggestions.
- Suggestion Gate was not run.
- No production Recommendation, PaperTrade, Review, or Memory records were written.
- No production cache or provider config mutation.
- No raw payload, request URL, or token value storage.
- No broker API, webhook, order placement, live order signal, or position size.
- Dashboard Contract remains unchanged.

## Next

`V2.13-W Finnhub Quote Multi-Symbol Sandbox Result Brief` should present a
user-readable blocked-result brief explaining why `CRCL.US`, `MSFT.US`, and
`NVDA.US` are not promoted to simulation suggestions from this sandbox branch.

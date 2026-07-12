# V2.13-U Finnhub Quote Multi-Symbol Historical Case Assembly

Status: PASS

## Scope

V2.13-U consumes the V2.13-T sandbox candidate bindings for `CRCL.US`,
`MSFT.US`, and `NVDA.US`, then fetches bounded EODHD daily bars into a
run-specific normalized cache and assembles rolling historical cases.

Finnhub remains the quote-context evidence source for this branch. EODHD is
used only for bounded historical daily bars because the current Finnhub candle
endpoint is not available on the active key. This stage does not run sandbox
evaluation or enable user-facing suggestions.

## Evidence

- Command: `python3 scripts/validate_v2_13_u_finnhub_quote_multi_symbol_historical_case_assembly.py --run-id v2_13_u_20260712_acceptance`
- Exit code: `0`
- Report JSON: `data/reports/v2_13_u_finnhub_quote_multi_symbol_historical_case_assembly_latest.json`
- Report MD: `data/reports/v2_13_u_finnhub_quote_multi_symbol_historical_case_assembly_latest.md`
- Marker: `data/reports/V2_13_U_FINNHUB_QUOTE_MULTI_SYMBOL_HISTORICAL_CASE_ASSEMBLY_PASS.marker`
- Assembly JSON: `data/processed/v2_13_u_acceptance/v2_13_u_20260712_acceptance/finnhub_quote_multi_symbol_historical_case_assembly.json`
- Historical cases JSONL: `data/processed/v2_13_u_acceptance/v2_13_u_20260712_acceptance/finnhub_quote_multi_symbol_historical_cases.jsonl`
- Daily bars fetch JSON: `data/processed/v2_13_u_acceptance/v2_13_u_20260712_acceptance/finnhub_quote_multi_symbol_daily_bar_fetch_results.json`
- Normalized cache dir: `data/processed/v2_13_u_acceptance/v2_13_u_20260712_acceptance/normalized_daily_bar_cache`
- Unit tests: `./.venv/bin/pytest tests/test_finnhub_quote_multi_symbol_historical_case_assembly_v2_13_u.py -q`
- Adjacent tests: `./.venv/bin/pytest tests/test_finnhub_free_probe_v2_13_a.py ... tests/test_finnhub_quote_multi_symbol_historical_case_assembly_v2_13_u.py -q`

## Result

- Candidate packets: `3`
- Daily bars cases: `3`
- Historical rolling cases: `81`
- Symbols: `CRCL.US`, `MSFT.US`, `NVDA.US`
- Market: `US`
- Network used: `true`
- Sandbox evaluation run: `false`
- Sandbox evaluation required: `true`
- Suggestion Gate required: `true`
- User-facing suggestion allowed: `false`
- Next stage: `V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation`

## Hashes

- Report JSON SHA256: `e9070b396a5a076d4fa2c1e07a54732bf76234532b3459940ad91ea95775db3d`
- Marker SHA256: `968b37a350dd7c2b8a65857046af9809887c1258761a3f3b3652d3107f31b202`
- Historical cases JSONL SHA256: `e864700fd7dde19d3291378c4f090d720e3a3ab98ba626f464cf2d622e5a176d`
- Daily bars fetch JSON SHA256: `d8131d41cae2b2ece681d54b185b8dcec45437c99db74559b7e3d7f695a695d9`

## Tests

- `./.venv/bin/pytest tests/test_finnhub_quote_multi_symbol_historical_case_assembly_v2_13_u.py -q`
  - Result: `6 passed`
- Adjacent Finnhub V2.13 A-U tests
  - Result: `123 passed`

## Safety

- Historical case assembly only.
- EODHD fetch is bounded and writes only run-specific normalized artifacts.
- No sandbox evaluation was run in this stage.
- No user-facing suggestion is enabled.
- No production Recommendation, PaperTrade, Review, or Memory records were written.
- No production cache or provider config mutation.
- No raw payload, request URL, or token value storage.
- No broker API, webhook, order placement, live order signal, or position size.
- Dashboard Contract remains unchanged.

## Next

`V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation` should evaluate the 81
assembled historical cases before any Suggestion Gate or user-facing simulation
brief is allowed.

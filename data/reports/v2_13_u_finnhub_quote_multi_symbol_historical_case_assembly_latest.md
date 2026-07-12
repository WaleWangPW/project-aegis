# V2.13-U Finnhub Quote Multi-Symbol Historical Case Assembly

- status: `PASS`
- run_id: `v2_13_u_20260712_acceptance`
- candidate_packet_count: `3`
- daily_bars_case_count: `3`
- historical_case_count: `81`
- symbols: `['CRCL.US', 'MSFT.US', 'NVDA.US']`
- sandbox_evaluation_run: `False`
- user_facing_suggestion_allowed: `False`
- next_stage: `V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation`

## Candidate Packets

### CRCL.US

- status: `historical_cases_assembled`
- strategy_id: `strategy_crcl_us_finnhub_multi_quote_context_probe`
- daily_bars_case_id: `us_crcl_us_eodhd_daily_bars`
- historical_case_count: `27`

### MSFT.US

- status: `historical_cases_assembled`
- strategy_id: `strategy_msft_us_finnhub_multi_quote_context_probe`
- daily_bars_case_id: `us_msft_us_eodhd_daily_bars`
- historical_case_count: `27`

### NVDA.US

- status: `historical_cases_assembled`
- strategy_id: `strategy_nvda_us_finnhub_multi_quote_context_probe`
- daily_bars_case_id: `us_nvda_us_eodhd_daily_bars`
- historical_case_count: `27`

## Boundary

- Historical case assembly only.
- EODHD is used only for bounded historical daily bars in a run-specific cache.
- Sandbox evaluation is not run in this stage.
- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.

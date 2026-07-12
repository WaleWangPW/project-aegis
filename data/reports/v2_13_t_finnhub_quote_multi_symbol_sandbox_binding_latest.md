# V2.13-T Finnhub Quote Multi-Symbol Sandbox Candidate Binding

- status: `PASS`
- run_id: `v2_13_t_20260712_acceptance`
- binding_count: `3`
- symbols: `['CRCL.US', 'MSFT.US', 'NVDA.US']`
- binding_statuses: `['bound_pending_historical_cases']`
- next_stage: `V2.13-U Finnhub Quote Multi-Symbol Historical Case Assembly`

## Bindings

### CRCL.US

- binding_id: `bind_finnhub_quote_context_us_crcl_finnhub_quote_multi_symbol_sandbox_candidate`
- binding_status: `bound_pending_historical_cases`
- strategy_id: `strategy_crcl_us_finnhub_multi_quote_context_probe`
- required_next_inputs: `['historical_cases', 'sandbox_evaluation', 'suggestion_gate', 'risk_checks']`
- user_facing_suggestion_allowed: `False`

### MSFT.US

- binding_id: `bind_finnhub_quote_context_us_msft_finnhub_quote_multi_symbol_sandbox_candidate`
- binding_status: `bound_pending_historical_cases`
- strategy_id: `strategy_msft_us_finnhub_multi_quote_context_probe`
- required_next_inputs: `['historical_cases', 'sandbox_evaluation', 'suggestion_gate', 'risk_checks']`
- user_facing_suggestion_allowed: `False`

### NVDA.US

- binding_id: `bind_finnhub_quote_context_us_nvda_finnhub_quote_multi_symbol_sandbox_candidate`
- binding_status: `bound_pending_historical_cases`
- strategy_id: `strategy_nvda_us_finnhub_multi_quote_context_probe`
- required_next_inputs: `['historical_cases', 'sandbox_evaluation', 'suggestion_gate', 'risk_checks']`
- user_facing_suggestion_allowed: `False`

## Boundary

- Sandbox candidate binding only.
- A single quote snapshot is not a historical sandbox result.
- Historical cases, sandbox evaluation, Suggestion Gate, and risk checks are still required.
- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.

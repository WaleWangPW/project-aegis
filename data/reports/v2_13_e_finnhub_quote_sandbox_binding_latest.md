# V2.13-E Finnhub Quote Context To Sandbox Candidate Binding

- status: `PASS`
- run_id: `v2_13_e_20260712_acceptance`
- binding_count: `1`
- symbols: `['AAPL.US']`
- binding_statuses: `['bound_pending_historical_cases']`
- next_stage: `V2.13-F Finnhub Quote Context Historical Case Assembly`

## Bindings

### bind_finnhub_quote_context_us_aapl_finnhub_quote_sandbox_candidate

- binding_status: `bound_pending_historical_cases`
- symbol: `AAPL.US`
- strategy_id: `strategy_aapl_us_finnhub_quote_context_probe`
- required_next_inputs: `['historical_cases', 'sandbox_evaluation', 'suggestion_gate', 'risk_checks']`
- user_facing_suggestion_allowed: `False`

## Boundary

- Sandbox candidate binding only.
- A single quote snapshot is not a historical sandbox result.
- Historical cases, sandbox evaluation, Suggestion Gate, and risk checks are still required.
- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.

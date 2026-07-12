# V2.13-G Finnhub Quote Context Sandbox Evaluation

- status: `PASS`
- run_id: `v2_13_g_20260712_restart_evidence_check`
- candidate_count: `1`
- historical_case_count: `8`
- strategy_pass_count: `1`
- strategy_fail_count: `0`
- passing_strategies: `['strategy_aapl_us_finnhub_quote_context_probe']`
- user_facing_suggestion_allowed: `False`
- next_stage: `V2.13-H Finnhub Quote Sandbox Evidence To Suggestion Gate Draft`

## Sandbox Results

### strategy_aapl_us_finnhub_quote_context_probe

- status: `PASS`
- sample_count: `8`
- win_rate: `0.625`
- average_return: `0.009053844504582794`
- max_drawdown: `-0.04843987946732331`
- failed_reasons: `[]`

## Boundary

- Sandbox evaluation only; Suggestion Gate is still required.
- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.

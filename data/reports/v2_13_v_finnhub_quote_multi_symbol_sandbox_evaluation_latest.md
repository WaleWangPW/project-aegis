# V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation

- status: `PASS`
- run_id: `v2_13_v_20260712_acceptance`
- candidate_count: `3`
- historical_case_count: `81`
- strategy_pass_count: `0`
- strategy_fail_count: `3`
- passing_strategies: `[]`
- failing_strategies: `['strategy_crcl_us_finnhub_multi_quote_context_probe', 'strategy_msft_us_finnhub_multi_quote_context_probe', 'strategy_nvda_us_finnhub_multi_quote_context_probe']`
- user_facing_suggestion_allowed: `False`
- next_stage: `V2.13-W Finnhub Quote Multi-Symbol Sandbox Result Brief`

## Sandbox Results

### strategy_crcl_us_finnhub_multi_quote_context_probe

- status: `FAIL`
- sample_count: `27`
- win_rate: `0.37037037037037035`
- average_return: `-0.015221498572253377`
- max_drawdown: `-0.17693522906793036`
- failed_reasons: `['win_rate_below_threshold', 'average_return_below_threshold', 'max_drawdown_breached']`

### strategy_msft_us_finnhub_multi_quote_context_probe

- status: `FAIL`
- sample_count: `27`
- win_rate: `0.4444444444444444`
- average_return: `-0.006348927822844228`
- max_drawdown: `-0.04702791109204496`
- failed_reasons: `['win_rate_below_threshold', 'average_return_below_threshold']`

### strategy_nvda_us_finnhub_multi_quote_context_probe

- status: `FAIL`
- sample_count: `27`
- win_rate: `0.4444444444444444`
- average_return: `-0.001959098221603719`
- max_drawdown: `-0.06553553461995787`
- failed_reasons: `['win_rate_below_threshold', 'average_return_below_threshold']`

## Boundary

- Sandbox evaluation only.
- Failed sandbox results are not promoted to suggestions.
- Suggestion Gate is not run in this stage.
- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.

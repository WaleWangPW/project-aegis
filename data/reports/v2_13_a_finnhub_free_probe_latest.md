# V2.13-A Finnhub Free Probe

- status: `PASS`
- run_id: `v2_13_a_20260712_after_codex_restart_probe`
- quote_status: `pass`
- social_sentiment_status: `blocked_plan_or_rate_limit`
- pass_count: `1`
- blocked_count: `1`
- fail_count: `0`
- next_stage: `V2.13-B Finnhub Metadata Activation`

## Results

### Finnhub quote AAPL

- status: `pass`
- env_present: `True`
- env_var_used: `AEGIS_FINNHUB_API_KEY`
- http_status: `200`
- blocked_by: `[]`
- summary: `{'shape': 'dict', 'keys': ['c', 'd', 'dp', 'h', 'l', 'o', 'pc', 't'], 'numeric_key_count': 8, 'has_current_price': True, 'has_previous_close': True}`

### Finnhub social_sentiment AAPL

- status: `blocked_plan_or_rate_limit`
- env_present: `True`
- env_var_used: `AEGIS_FINNHUB_API_KEY`
- http_status: `403`
- blocked_by: `['social_sentiment_not_available_on_current_plan_or_rate_limit']`
- summary: `{'shape': 'dict', 'keys': ['error'], 'reddit_items': None, 'twitter_items': None, 'has_social_series': False, 'error_text_sha256': '15813e51adff8f5c1b10e99c6298b34a8b82c8ce55db18c7bc8a4bd48a719cf9', 'error_text_present': True}`

## Boundary

- Finnhub free endpoint probe only.
- Social sentiment may be plan-gated; a plan/rate-limit block is recorded, not bypassed.
- Env var names only; no token values.
- No request URL or raw payload storage.
- No real trade, broker API, trading webhook, order placement, or production record mutation.
- Dashboard Contract unchanged.

# V2.12-B H-US Provider Metadata Activation

- status: `PASS`
- run_id: `v2_12_b_20260712_acceptance`
- h_route: `eodhd_primary_ready`
- us_route: `eodhd_primary_twelve_backup_ready`
- twelve_data_h_status: `blocked_fetch_error`
- next_stage: `V2.12-C H-US Historical Cache Readiness Dry Run`

## Route Proposals

### h_daily_bars_eodhd_primary

- market: `H`
- data_type: `daily_bars`
- primary_provider: `eodhd`
- fallback_providers: `[]`
- status: `ready_for_metadata`
- required_env_vars: `['AEGIS_EODHD_API_TOKEN']`
- forbidden_uses: `['real_trade', 'broker_api', 'trading_webhook', 'order_placement']`

### us_daily_bars_eodhd_primary_twelve_backup

- market: `US`
- data_type: `daily_bars`
- primary_provider: `eodhd`
- fallback_providers: `['twelve_data']`
- status: `ready_for_metadata`
- required_env_vars: `['AEGIS_EODHD_API_TOKEN', 'AEGIS_TWELVE_DATA_API_KEY']`
- forbidden_uses: `['real_trade', 'broker_api', 'trading_webhook', 'order_placement']`

### h_daily_bars_twelve_data_review

- market: `H`
- data_type: `daily_bars`
- primary_provider: `twelve_data`
- fallback_providers: `[]`
- status: `blocked_fetch_error`
- required_env_vars: `['AEGIS_TWELVE_DATA_API_KEY']`
- forbidden_uses: `['suggestion_inputs', 'production_routing', 'real_trade', 'order_placement']`

## Boundary

- Metadata/routing proposal only.
- Env var names only; no token values.
- No request URL or raw payload storage.
- Production provider config is not mutated.
- Suggestion path is not enabled by this stage.
- No real trade, broker API, trading webhook, or order placement.
- Dashboard Contract unchanged.

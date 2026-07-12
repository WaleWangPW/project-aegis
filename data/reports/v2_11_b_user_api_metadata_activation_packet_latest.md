# V2.11-B User API Metadata Activation Packet

- status: `PASS`
- connector_id: `api_user_candidate_refresh_approved_env`
- current_intake_status: `blocked_missing_metadata`
- tushare_status: `a_share_core_ready`
- tushare_token_present: `True`
- tushare_network_available: `True`
- local_config_path: `config/external_api_connectors.local.json`
- user_template_path: `config/external_api_connectors.user-template.json`
- required_env_vars: `['AEGIS_CANDIDATE_REFRESH_API_KEY']`

## Tushare First

- role: `primary_a_share_data_source`
- required_env_var_name: `TUSHARE_TOKEN`
- a_share_core_ready: `True`
- allowed_uses: `['a_share_data_read', 'historical_sandbox', 'strategy_research_inputs', 'simulation_only_suggestions']`
- forbidden_uses: `['real_trade', 'broker_api', 'trading_webhook', 'order_placement']`

## Fill These Non-Secret Metadata Fields

- `connector_id`
- `name`
- `provider_type`
- `markets`
- `base_url`
- `auth_method`
- `required_env_vars`
- `license_status`
- `retention_policy`
- `allowed_purposes`
- `can_connect`
- `endpoint_path`
- `request_query_template`
- `candidate_payload_schema`

## Never Put These In Files Or Chat

- api_key value
- secret value
- cookie
- bearer token
- authorization header value
- broker credential
- trading webhook secret
- password
- oauth refresh token

## User Steps

- Copy config/external_api_connectors.user-template.json to config/external_api_connectors.local.json.
- Replace only non-secret metadata fields such as base_url, endpoint_path, markets, allowed_purposes, and schema field names.
- Set the actual API key only in the named local environment variable; never paste the value into chat, repo, Vault, or JSON.
- Run V2.10-B metadata intake again; only proceed when status is ready_for_live_readiness_check or blocked_missing_env_vars with clear env var names.

## Ready Criteria

- config/external_api_connectors.local.json exists and is gitignored.
- metadata contains connector_id api_user_candidate_refresh_approved_env.
- markets cover A, H, and US.
- allowed_purposes do not contain trade, trading, order, broker, or webhook.
- retention_policy is summary_only.
- candidate_payload_schema.candidate_summary_only is true.
- required local env var names are present, but values are never serialized.

## Boundary

- Metadata packet only.
- No network fetch.
- No API key values stored.
- No broker API.
- No trading webhook.
- No order placement.

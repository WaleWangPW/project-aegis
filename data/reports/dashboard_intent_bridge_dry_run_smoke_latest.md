# Dashboard Intent Bridge Dry-Run Smoke

- status: `PASS`
- base_url: `http://127.0.0.1:8080`
- blockers: `none`

## Checks

- http_200: `True`
- dry_run_status: `True`
- event_count_one: `True`
- latest_symbol_matches: `True`
- latest_action_matches: `True`
- no_feedback_latest_mutation: `True`
- no_event_log_mutation: `True`
- no_trading_side_effects: `True`

## Safety

- Dry-run only; latest feedback and event log must not change.
- No market data fetch, no secret values, no broker API, no order, no trading webhook.

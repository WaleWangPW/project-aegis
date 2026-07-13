# Dashboard Daily Use Smoke

- status: `PASS`
- base_url: `http://127.0.0.1:8080`
- blockers: `none`

## Checks

- bridge_health_ready: `True`
- bridge_safety_no_trading: `True`
- dashboard_html_available: `True`
- daily_readiness_ready: `True`
- daily_readiness_safety: `True`
- button_feedback_recorded: `True`
- button_feedback_no_trading_side_effects: `True`
- ranking_gate_blocks_suggestions: `True`
- retry_preflight_safe: `True`

## Safety

- Local dashboard only.
- No market data fetch, no secret values, no broker API, no order, no trading webhook.

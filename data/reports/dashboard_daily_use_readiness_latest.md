# Dashboard Daily Use Readiness

- status: `READY_FOR_SIMULATION_USE`
- usable_for: `simulation_research_only`
- blockers: `none`

## Summary

- total_candidates: `30`
- research_candidate_count: `13`
- news_enriched_count: `9`
- markets_passed: `['A', 'HK', 'US']`
- latest_feedback_symbol: `VRTX`
- latest_feedback_action: `aegis_more_news`
- real_click_acceptance_status: `ACCEPTED`
- real_click_symbol: `VRTX`
- real_click_action: `aegis_more_news`
- ranking_gate_approved_count: `0`
- user_facing_suggestion_allowed: `False`
- a_share_retry_status: `WAITING`
- a_share_retry_ready_to_run: `False`

## Checks

- dashboard_health_normal: `True`
- candidate_pool_available: `True`
- news_summary_available: `True`
- multi_market_available: `True`
- button_feedback_recorded: `True`
- button_feedback_has_no_trading_side_effects: `True`
- real_dashboard_click_accepted: `True`
- real_dashboard_click_safe: `True`
- ranking_gate_blocks_unapproved_strategy: `True`
- ranking_gate_has_no_trading_side_effects: `True`
- a_share_retry_preflight_available: `True`
- a_share_retry_preflight_safe: `True`

## Safety

- Simulation-only.
- No broker API, no order placement, no trading webhook, no secret values read.

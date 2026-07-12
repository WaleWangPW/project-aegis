# V2.11-F A-Share Tushare Strategy Candidate Rebuild

- status: `PASS`
- run_id: `v2_11_f_20260711_acceptance`
- source_failed_strategy_count: `2`
- rebuild_proposal_count: `2`
- user_facing_suggestion_count: `0`
- auto_applied_count: `0`
- next_stage: `V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run`

## Rebuild Proposals

### strategy_a_low_vol_dividend_defensive

- decision: `research_rebuild_only`
- candidate_status: `blocked_until_rebuilt_sandbox_pass`
- failed_reasons: `['win_rate_below_threshold', 'average_return_below_threshold', 'max_drawdown_breached']`
- rebuild_actions: `['add_market_regime_filter', 'tighten_drawdown_and_volatility_filter', 'require_event_risk_precheck', 'add_positive_momentum_confirmation', 'require_factor_score_margin', 'raise_liquidity_and_quality_floor', 'expand_historical_sample_before_retest']`
- minimum_total_sample_count: `24`

### strategy_a_value_quality_multifactor

- decision: `research_rebuild_only`
- candidate_status: `blocked_until_rebuilt_sandbox_pass`
- failed_reasons: `['average_return_below_threshold', 'max_drawdown_breached']`
- rebuild_actions: `['add_market_regime_filter', 'tighten_drawdown_and_volatility_filter', 'require_event_risk_precheck', 'add_positive_momentum_confirmation', 'require_factor_score_margin']`
- minimum_total_sample_count: `24`

## Boundary

- Research rebuild only.
- A-share remains blocked until rebuilt sandbox and Suggestion Gate pass.
- No real trade, broker API, trading webhook, order placement, live price, or position size.
- No production Recommendation/PaperTrade/Review/Memory record mutation.
- Dashboard Contract unchanged.

# A-share Tushare Source Deep Sandbox

- Status: `PASS`
- Generated At: `2026-07-12T22:21:01+08:00`
- Ready Hypotheses: `5`
- Pass Candidates: `0`
- Fail: `5`
- Feature Gap Blocked: `1`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

## Results

| Hypothesis | Disposition | Signal Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `hyp_a_tushare_capital_flow_accumulation` | `DEEP_SANDBOX_FAIL` | 9 | 0.33 | -0.1157 | -0.4927 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_institutional_ownership_stability` | `DEEP_SANDBOX_FAIL` | 30 | 0.20 | -0.0833 | -0.4927 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_holder_concentration_improvement` | `DEEP_SANDBOX_FAIL` | 13 | 0.38 | -0.0255 | -0.1942 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_factor_liquidity_quality_overlay` | `DEEP_SANDBOX_FAIL` | 26 | 0.35 | -0.0409 | -0.2518 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_governance_reward_alignment` | `DEEP_SANDBOX_FAIL` | 40 | 0.28 | -0.0617 | -0.4927 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold, source_signal_drawdown_breached |

## Blocked By Feature Gaps

`hyp_a_tushare_dragon_tiger_seat_confirmation`

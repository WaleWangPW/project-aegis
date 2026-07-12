# A-share Tushare Source Deep Sandbox

- Status: `PASS`
- Generated At: `2026-07-12T21:24:22+08:00`
- Ready Hypotheses: `5`
- Pass Candidates: `0`
- Fail: `5`
- Feature Gap Blocked: `1`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

## Results

| Hypothesis | Disposition | Signal Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `hyp_a_tushare_capital_flow_accumulation` | `DEEP_SANDBOX_FAIL` | 1 | 1.00 | 0.0581 | -0.1232 | source_signal_case_count_below_threshold |
| `hyp_a_tushare_institutional_ownership_stability` | `DEEP_SANDBOX_FAIL` | 6 | 0.33 | -0.0220 | -0.1232 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold |
| `hyp_a_tushare_holder_concentration_improvement` | `DEEP_SANDBOX_FAIL` | 4 | 0.25 | -0.0506 | -0.1770 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold |
| `hyp_a_tushare_factor_liquidity_quality_overlay` | `DEEP_SANDBOX_FAIL` | 5 | 0.40 | -0.0195 | -0.1232 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold |
| `hyp_a_tushare_governance_reward_alignment` | `DEEP_SANDBOX_FAIL` | 8 | 0.25 | -0.0394 | -0.1770 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold |

## Blocked By Feature Gaps

`hyp_a_tushare_dragon_tiger_seat_confirmation`

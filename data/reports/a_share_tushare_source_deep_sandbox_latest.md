# A-share Tushare Source Deep Sandbox

- Status: `PASS`
- Generated At: `2026-07-13T16:05:04+08:00`
- Ready Hypotheses: `5`
- Pass Candidates: `0`
- Fail: `5`
- Feature Gap Blocked: `0`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

## Results

| Hypothesis | Disposition | Signal Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `hyp_a_tushare_capital_flow_accumulation` | `DEEP_SANDBOX_FAIL` | 18 | 0.56 | -0.0308 | -0.4063 | source_signal_average_return_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_institutional_ownership_stability` | `DEEP_SANDBOX_FAIL` | 20 | 0.20 | -0.0199 | -0.3305 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_holder_concentration_improvement` | `DEEP_SANDBOX_FAIL` | 17 | 0.35 | -0.0207 | -0.3399 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_factor_liquidity_quality_overlay` | `DEEP_SANDBOX_FAIL` | 41 | 0.46 | 0.0097 | -0.3399 | source_signal_win_rate_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_governance_reward_alignment` | `DEEP_SANDBOX_FAIL` | 40 | 0.42 | 0.0085 | -0.3399 | source_signal_win_rate_below_threshold, source_signal_drawdown_breached |

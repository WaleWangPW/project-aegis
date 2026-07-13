# A-share Tushare Source Deep Sandbox

- Status: `PASS`
- Generated At: `2026-07-13T09:15:25+08:00`
- Ready Hypotheses: `5`
- Pass Candidates: `0`
- Fail: `5`
- Feature Gap Blocked: `0`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

## Results

| Hypothesis | Disposition | Signal Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `hyp_a_tushare_capital_flow_accumulation` | `DEEP_SANDBOX_FAIL` | 16 | 0.62 | 0.0146 | -0.4063 | source_signal_drawdown_breached |
| `hyp_a_tushare_institutional_ownership_stability` | `DEEP_SANDBOX_FAIL` | 20 | 0.30 | -0.0005 | -0.2561 | source_signal_win_rate_below_threshold, source_signal_average_return_below_threshold, source_signal_drawdown_breached |
| `hyp_a_tushare_holder_concentration_improvement` | `DEEP_SANDBOX_FAIL` | 16 | 0.56 | 0.0195 | -0.2890 | source_signal_drawdown_breached |
| `hyp_a_tushare_factor_liquidity_quality_overlay` | `DEEP_SANDBOX_FAIL` | 38 | 0.50 | 0.0184 | -0.3190 | source_signal_drawdown_breached |
| `hyp_a_tushare_governance_reward_alignment` | `DEEP_SANDBOX_FAIL` | 40 | 0.47 | 0.0172 | -0.3503 | source_signal_win_rate_below_threshold, source_signal_drawdown_breached |

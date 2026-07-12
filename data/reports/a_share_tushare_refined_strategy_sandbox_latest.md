# A-share Tushare Refined Strategy Sandbox

- Status: `PASS`
- Generated At: `2026-07-12T23:10:41+08:00`
- Refined Strategies: `5`
- Pass Candidates: `1`
- Ranking Impact Allowed: `False`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

| Strategy | Disposition | Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `refined_a_moneyflow_holder_concentration` 主力资金 + 筹码集中 | `REFINED_SANDBOX_PASS_CANDIDATE` | 3 | 0.67 | 0.0430 | -0.1436 | refined_signal_thresholds_passed |
| `refined_a_moneyflow_factor_veto` 主力资金 + 因子风险否决 | `REFINED_SANDBOX_FAIL` | 8 | 0.38 | -0.0571 | -0.2099 | refined_signal_win_rate_below_threshold, refined_signal_average_return_below_threshold, refined_signal_drawdown_breached |
| `refined_a_holder_factor_veto` 筹码集中 + 因子风险否决 | `REFINED_SANDBOX_FAIL` | 11 | 0.27 | -0.0478 | -0.2035 | refined_signal_win_rate_below_threshold, refined_signal_average_return_below_threshold, refined_signal_drawdown_breached |
| `refined_a_institutional_factor_veto` 机构持仓 + 因子风险否决 | `REFINED_SANDBOX_FAIL` | 21 | 0.29 | -0.0541 | -0.2518 | refined_signal_win_rate_below_threshold, refined_signal_average_return_below_threshold, refined_signal_drawdown_breached |
| `refined_a_moneyflow_holder_factor` 主力资金 + 筹码集中 + 因子 | `REFINED_SANDBOX_FAIL` | 1 | 1.00 | 0.0132 | -0.0383 | refined_signal_case_count_below_threshold |

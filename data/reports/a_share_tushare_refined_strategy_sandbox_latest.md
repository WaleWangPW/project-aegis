# A-share Tushare Refined Strategy Sandbox

- Status: `PASS`
- Generated At: `2026-07-13T10:29:51+08:00`
- Refined Strategies: `5`
- Pass Candidates: `0`
- Ranking Impact Allowed: `False`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

| Strategy | Disposition | Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `refined_a_moneyflow_holder_concentration` 主力资金 + 筹码集中 | `REFINED_SANDBOX_FAIL` | 4 | 0.75 | -0.0163 | -0.2890 | refined_signal_average_return_below_threshold, refined_signal_drawdown_breached |
| `refined_a_moneyflow_factor_veto` 主力资金 + 因子风险否决 | `REFINED_SANDBOX_FAIL` | 8 | 0.88 | 0.1388 | -0.2890 | refined_signal_drawdown_breached |
| `refined_a_holder_factor_veto` 筹码集中 + 因子风险否决 | `REFINED_SANDBOX_FAIL` | 11 | 0.55 | 0.0281 | -0.2890 | refined_signal_drawdown_breached |
| `refined_a_institutional_factor_veto` 机构持仓 + 因子风险否决 | `REFINED_SANDBOX_FAIL` | 12 | 0.33 | 0.0120 | -0.2337 | refined_signal_win_rate_below_threshold, refined_signal_drawdown_breached |
| `refined_a_moneyflow_holder_factor` 主力资金 + 筹码集中 + 因子 | `REFINED_SANDBOX_FAIL` | 2 | 0.50 | -0.0763 | -0.2890 | refined_signal_average_return_below_threshold, refined_signal_drawdown_breached |

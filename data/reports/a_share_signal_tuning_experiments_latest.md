# A-share Signal Tuning Experiments

- Status: `PASS`
- Generated At: `2026-07-13T16:05:04+08:00`
- Experiments: `4`
- Pass Candidates: `0`
- Fail: `4`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

## Results

| Experiment | Disposition | Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `tuned_a_moneyflow_factor_veto` | `TUNED_EXPERIMENT_FAIL` | 12 | 0.75 | 0.0611 | -0.3399 | tuned_signal_drawdown_breached |
| `tuned_a_holder_concentration_strict` | `TUNED_EXPERIMENT_FAIL` | 17 | 0.35 | -0.0207 | -0.3399 | tuned_signal_win_rate_below_threshold, tuned_signal_average_return_below_threshold, tuned_signal_drawdown_breached |
| `tuned_a_institutional_factor_trend_filter` | `TUNED_EXPERIMENT_FAIL` | 8 | 0.38 | 0.0253 | -0.3305 | tuned_signal_win_rate_below_threshold, tuned_signal_drawdown_breached |
| `tuned_a_governance_veto_only` | `TUNED_EXPERIMENT_FAIL` | 40 | 0.42 | 0.0085 | -0.3399 | tuned_signal_win_rate_below_threshold, tuned_signal_drawdown_breached, veto_or_diagnostic_only_not_rankable |

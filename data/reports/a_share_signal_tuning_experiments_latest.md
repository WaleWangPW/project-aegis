# A-share Signal Tuning Experiments

- Status: `PASS`
- Generated At: `2026-07-13T01:47:00+08:00`
- Experiments: `4`
- Pass Candidates: `1`
- Fail: `3`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

## Results

| Experiment | Disposition | Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `tuned_a_moneyflow_factor_veto` | `TUNED_EXPERIMENT_FAIL` | 10 | 0.40 | -0.0847 | -0.3743 | tuned_signal_win_rate_below_threshold, tuned_signal_average_return_below_threshold, tuned_signal_drawdown_breached |
| `tuned_a_holder_concentration_strict` | `TUNED_EXPERIMENT_FAIL` | 16 | 0.31 | -0.0534 | -0.2035 | tuned_signal_win_rate_below_threshold, tuned_signal_average_return_below_threshold, tuned_signal_drawdown_breached |
| `tuned_a_institutional_factor_trend_filter` | `TUNED_EXPERIMENT_PASS_CANDIDATE` | 4 | 0.75 | 0.0377 | -0.1602 | tuned_signal_thresholds_passed |
| `tuned_a_governance_veto_only` | `TUNED_EXPERIMENT_FAIL` | 40 | 0.28 | -0.0617 | -0.4927 | tuned_signal_win_rate_below_threshold, tuned_signal_average_return_below_threshold, tuned_signal_drawdown_breached, veto_or_diagnostic_only_not_rankable |

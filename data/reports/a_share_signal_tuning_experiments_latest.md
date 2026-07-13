# A-share Signal Tuning Experiments

- Status: `PASS`
- Generated At: `2026-07-13T08:36:06+08:00`
- Experiments: `4`
- Pass Candidates: `0`
- Fail: `4`
- Boundary: derived features only; no raw payload, no broker, no order, no trading webhook, no ranking impact.

## Results

| Experiment | Disposition | Cases | Win Rate | Avg Return | Max Drawdown | Reasons |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `tuned_a_moneyflow_factor_veto` | `TUNED_EXPERIMENT_FAIL` | 8 | 0.88 | 0.1388 | -0.2890 | tuned_signal_drawdown_breached |
| `tuned_a_holder_concentration_strict` | `TUNED_EXPERIMENT_FAIL` | 16 | 0.56 | 0.0195 | -0.2890 | tuned_signal_drawdown_breached |
| `tuned_a_institutional_factor_trend_filter` | `TUNED_EXPERIMENT_FAIL` | 6 | 0.33 | 0.0404 | -0.2337 | tuned_signal_win_rate_below_threshold, tuned_signal_drawdown_breached |
| `tuned_a_governance_veto_only` | `TUNED_EXPERIMENT_FAIL` | 40 | 0.47 | 0.0172 | -0.3503 | tuned_signal_win_rate_below_threshold, tuned_signal_drawdown_breached, veto_or_diagnostic_only_not_rankable |

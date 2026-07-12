# P22.3 Dashboard Backtest Evidence

- success: True
- reason: N/A

## Commands
| command | exit_code |
|---|---:|
| make validate-a-share-backtest-dry-run | 0 |
| make validate-aegis-health-status | 0 |
| make verify-aegis-evidence-gate | 0 |
| make refresh-feishu-dry-run | 0 |
| make refresh-aegis-daily-digest | 0 |
| make validate-aegis-daily-digest | 0 |
| make audit-aegis-pipeline-evidence | 0 |
| make redteam-aegis-pipeline-validator | 0 |
| make verify-aegis-evidence-gate-base | 0 |
| make update-aegis-pipeline-history | 0 |
| make validate-aegis-pipeline-history | 0 |
| make build-aegis-health-status | 0 |
| make validate-aegis-health-status | 0 |
| make validate-a-share-backtest-dry-run | 0 |
| make verify-aegis-evidence-gate | 0 |

## Page Checks
| check | result |
|---|---|
| dashboard_index_exists | PASS |
| backtest_section_present | PASS |
| backtest_json_fetch_present | PASS |
| static_snapshot_label_present | PASS |
| lookahead_bias_warning_present | PASS |
| dry_run_label_present | PASS |
| safety_flags_present | PASS |
| metrics_present | PASS |
| benchmark_present | PASS |
| degrade_text_present | PASS |
| no_secret_value_detected | PASS |
| no_real_send_call_detected | PASS |
| no_trading_call_detected | PASS |

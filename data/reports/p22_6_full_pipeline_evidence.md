# Project Aegis P22.6 Full Pipeline Evidence

- success: True
- reason: N/A

## Commands
| command | exit_code | result |
|---|---:|---|
| make validate-a-share-strategy-definition | 0 | PASS |
| make validate-a-share-backtest-dry-run | 0 | PASS |
| make p22-4-filemode | 0 | PASS |
| make p22-5-filemode | 0 | PASS |
| make validate-a-share-backtest-history | 0 | PASS |
| make validate-aegis-health-status | 0 | PASS |
| make verify-aegis-evidence-gate | 0 | PASS |

## Checks
| check | result |
|---|---|
| p22_2_pass_marker | PASS |
| p22_3_pass_marker | PASS |
| p22_4_pass_marker | PASS |
| p22_5_pass_marker | PASS |
| health_json_exists | PASS |
| backtest_json_exists | PASS |
| backtest_history_json_exists | PASS |
| dashboard_exists | PASS |
| dashboard_contract_v2 | PASS |
| no_secret_value_detected | PASS |
| no_send_call_detected | PASS |
| no_trading_call_detected | PASS |

## Summary
- health_status: NORMAL
- health_label: 正常
- gate_overall_verdict: PASS
- history: {'runs_count': 20, 'latest_run_id': 'bt_run_20260710_143250_hist_20260712_080022', 'latest_result': 'PASS', 'retention_limit': 20}
- backtest: {'strategy_id': 'a_share_watchlist_v1', 'selected_symbols_count': 20, 'valid_price_series_count': 20, 'total_return': -0.132762, 'annualized_return': -0.361538, 'max_drawdown': -0.157806, 'volatility': 0.139429, 'sharpe': -2.59298, 'win_rate': 0.4875, 'benchmark_total_return': 0.040267, 'excess_return': -0.173029, 'dry_run': True, 'sent': False, 'trading_called': False}

## Safety
- dry_run: true
- sent: false
- webhook_called: false
- trading_called: false
- cron_modified: false

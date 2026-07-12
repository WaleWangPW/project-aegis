# P22.2 Backtest Dry-run Evidence

- overall_success: True

## Command Results

| command | exit_code |
|---|---:|
| make validate-a-share-strategy-definition | 0 |
| make run-a-share-backtest-dry-run | 0 |
| make validate-a-share-backtest-dry-run | 0 |
| make validate-aegis-health-status | 0 |
| make verify-aegis-evidence-gate | 0 |

## Output Files

- backtest_json: EXISTS
- backtest_md: EXISTS
- input_json: EXISTS
- validation_json: EXISTS

## Safety

- dry_run: true
- sent: false
- webhook_called: false
- trading_called: false
- cron_modified: false

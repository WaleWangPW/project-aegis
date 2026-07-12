# Project Aegis V2.1-A Acceptance Report

Status: `V2.1-A PASS`

Date: `2026-07-11`

Acceptance target: `V2.1-A Historical Strategy Sandbox`

## What V2.1-A Proves

`V2.1-A Historical Strategy Sandbox` proves that Project Aegis can evaluate
explicit strategy candidates against historical cases before allowing those
strategies to influence user-facing suggestions.

This is not real trading, broker integration, automatic strategy mutation, or
Dashboard work.

## Evidence

Validation command:

```bash
.venv/bin/python scripts/validate_v2_1_a_historical_strategy_sandbox.py --run-id v2_1_a_20260711_acceptance
```

Exit code: `0`

PASS marker:

- `data/reports/V2_1_A_HISTORICAL_STRATEGY_SANDBOX_PASS.marker`

Reports:

- `data/reports/v2_1_a_historical_strategy_sandbox_latest.json`
- `data/reports/v2_1_a_historical_strategy_sandbox_latest.md`

Run artifacts:

- `data/processed/v2_1_a_acceptance/v2_1_a_20260711_acceptance/strategy_candidates.json`
- `data/processed/v2_1_a_acceptance/v2_1_a_20260711_acceptance/historical_strategy_cases.jsonl`

Hashes:

- `strategy_candidates.json`: `bfce1ae6bd2d1c314492ace6eb66995f6cda7841ea19c5fde4c07ad574884be1`
- `historical_strategy_cases.jsonl`: `b2cc113d257e4ace89a00807b14fa95d318567bb2ec79af8547c2449ba7cb1bc`
- `report_json`: `21b1d5f912fcfee947616ff4a0bf0bf8e7629d60b88415c9725cec155db9bef2`
- `report_md`: `c83f4e4ff55bce50f34df3e35fd94828c0253e17d28d5732362d0fe90801165f`

## Result Summary

- Candidate strategies: `2`
- Historical sandbox cases: `8`
- Local historical cache files detected: `222`
- Passing strategies: `low_volatility_dividend_a`
- Failing strategies: `raw_momentum_us`

Passing strategy metrics:

- Strategy: `low_volatility_dividend_a`
- Win rate: `0.75`
- Average return: `0.02125`
- Max drawdown: `-0.047`
- Sample count: `4`

Failing strategy evidence:

- Strategy: `raw_momentum_us`
- Failed reasons: `win_rate_below_threshold`, `average_return_below_threshold`, `max_drawdown_breached`
- Risk flags included `drawdown_breach` and `crowding_risk`

## Safety Boundaries

Confirmed:

- `simulation_only=true`
- `network_used=false`
- `production_records_written=false`
- `dashboard_contract_changed=false`
- `no_real_trade=true`
- `no_broker_api=true`
- `no_webhook=true`
- `no_secret_storage=true`
- `no_strategy_auto_mutation=true`
- `suggestion_gate_still_required=true`

## Regression Evidence

Targeted tests:

```bash
.venv/bin/python -m pytest tests/test_strategy_sandbox_v2_1_a.py -q
```

Result: `4 passed in 0.12s`

Related regression:

```bash
.venv/bin/python -m pytest tests/test_strategy_sandbox_v2_1_a.py tests/test_official_source_fetcher_v2_0_f.py tests/test_external_source_policy_v2_0_e.py tests/test_event_timeline_v2_0_d.py tests/test_research_workspace_v2_0_c.py tests/test_portfolio_aware_brief_v2_0_b.py tests/test_portfolio_foundation_v2_0_a.py tests/test_review_system_v1_5.py tests/test_validate_v1_0_single_cycle.py tests/test_run_backtest.py tests/test_backtest_metrics.py tests/test_time_travel_no_future_data.py -q
```

Result: `57 passed in 0.71s`

## Next Target

After `V2.1-A PASS`, the next product target is `V2.1-B Strategy Candidate
Library`: persist approved strategy candidates and make the sandbox reusable
across A-share, U.S., and Hong Kong candidate families.

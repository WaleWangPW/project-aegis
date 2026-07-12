# V2.14-C Refreshed Candidate Historical Sandbox

- status: `PASS`
- run_id: `v2_14_c_20260712_acceptance`
- covered_candidate_count: `3`
- missing_coverage_count: `3`
- historical_case_count: `3`
- strategy_pass_count: `1`
- strategy_fail_count: `1`
- next_stage: `V2.14-D Refreshed Candidate Suggestion Gate`

## Covered Candidates

- `600519.SH` / `A`: `historical_case_available`
- `600036.SH` / `A`: `historical_case_available`
- `00700.HK` / `H`: `historical_case_available`

## Missing Coverage

- `601398.SH` / `A`: `no_source_case_for_symbol`
- `00005.HK` / `H`: `no_source_case_for_symbol`
- `00941.HK` / `H`: `no_source_case_for_symbol`

## Sandbox Results

- `strategy_a_low_vol_dividend_defensive` status=`FAIL` sample_count=`1` average_return=`-0.03752763164658912`
- `strategy_h_low_vol_dividend` status=`PASS` sample_count=`1` average_return=`0.11297071129707119`

## Boundary

- Historical sandbox only.
- Missing coverage is explicit and cannot be treated as a pass.
- Not a user-facing suggestion.
- Suggestion Gate is still required.
- No real trade, broker API, webhook, order placement, live order signal, or position size.

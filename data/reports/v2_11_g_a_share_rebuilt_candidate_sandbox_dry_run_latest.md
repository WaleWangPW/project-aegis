# V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run

- status: `PASS`
- run_id: `v2_11_g_20260711_acceptance`
- rebuilt_candidate_count: `2`
- expanded_case_count: `48`
- strategy_pass_count: `0`
- strategy_fail_count: `2`
- a_share_reentry_allowed: `False`
- next_stage: `V2.11-H A-Share Blocked Evidence To User Brief Refresh`

## Results

### strategy_a_low_vol_dividend_defensive

- status: `FAIL`
- sample_count: `24`
- win_rate: `0.375`
- average_return: `-0.012811082628493268`
- max_drawdown: `-0.12505427702996108`
- failed_reasons: `['win_rate_below_threshold', 'average_return_below_threshold', 'max_drawdown_breached']`

### strategy_a_value_quality_multifactor

- status: `FAIL`
- sample_count: `24`
- win_rate: `0.4583333333333333`
- average_return: `-0.005080515453788111`
- max_drawdown: `-0.22160094173042966`
- failed_reasons: `['win_rate_below_threshold', 'average_return_below_threshold', 'max_drawdown_breached']`

## Boundary

- Expanded historical sandbox only.
- A-share remains blocked because no rebuilt strategy passed.
- No real trade, broker API, trading webhook, order placement, live price, or position size.
- No production Recommendation/PaperTrade/Review/Memory record mutation.
- Dashboard Contract unchanged.

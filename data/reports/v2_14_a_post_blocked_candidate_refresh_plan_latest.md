# V2.14-A Post-Blocked Candidate Pool Refresh Plan

- status: `PASS`
- run_id: `v2_14_a_20260712_acceptance`
- removed_candidate_count: `3`
- retained_candidate_count: `6`
- retained_markets: `['A', 'H']`
- replacement_required_markets: `['US']`
- next_stage: `V2.14-B Candidate Pool Live Refresh From Approved Routes`

## Removed Candidates

- `CRCL` / `US`: `blocked_by_v2_13_w_multi_symbol_sandbox_result_brief`
- `MSFT` / `US`: `blocked_by_v2_13_w_multi_symbol_sandbox_result_brief`
- `NVDA` / `US`: `blocked_by_v2_13_w_multi_symbol_sandbox_result_brief`

## Route Plan

- `A` -> `tushare_a_share_candidate_refresh` status=`ready_for_live_refresh` retained=`3`
- `H` -> `h_share_h_us_provider_candidate_refresh` status=`ready_for_h_us_refresh` retained=`3`
- `US` -> `us_candidate_replacement_required` status=`blocked_until_replacement_candidates_found` retained=`0`

## Boundary

- Candidate refresh plan only.
- Not a user-facing suggestion.
- Blocked candidates are removed from the next candidate pool.
- Every route still requires historical sandbox and Suggestion Gate.
- No real trade, broker API, webhook, order placement, live order signal, or position size.

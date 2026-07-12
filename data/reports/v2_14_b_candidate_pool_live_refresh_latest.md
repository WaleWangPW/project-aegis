# V2.14-B Candidate Pool Live Refresh From Approved Routes

- status: `PASS`
- run_id: `v2_14_b_20260712_acceptance`
- refreshed_candidate_count: `6`
- refreshed_markets: `['A', 'H']`
- replacement_required_markets: `['US']`
- next_stage: `V2.14-C Refreshed Candidate Historical Sandbox`

## Refreshed Candidates

- `600519.SH` / `A` via `tushare_a_share_candidate_refresh` status=`refreshed_pending_historical_sandbox`
- `600036.SH` / `A` via `tushare_a_share_candidate_refresh` status=`refreshed_pending_historical_sandbox`
- `601398.SH` / `A` via `tushare_a_share_candidate_refresh` status=`refreshed_pending_historical_sandbox`
- `00700.HK` / `H` via `h_share_h_us_provider_candidate_refresh` status=`refreshed_pending_historical_sandbox`
- `00005.HK` / `H` via `h_share_h_us_provider_candidate_refresh` status=`refreshed_pending_historical_sandbox`
- `00941.HK` / `H` via `h_share_h_us_provider_candidate_refresh` status=`refreshed_pending_historical_sandbox`

## Replacement Requests

- `US`: `replace_blocked_us_multi_symbol_candidates` status=`open_pending_replacement_candidates` blocked=`['CRCL', 'MSFT', 'NVDA']`

## Boundary

- Candidate pool refresh only.
- Not a user-facing suggestion.
- Historical sandbox and Suggestion Gate remain required.
- Blocked symbols from V2.13-W are not reused.
- No real trade, broker API, webhook, order placement, live order signal, or position size.

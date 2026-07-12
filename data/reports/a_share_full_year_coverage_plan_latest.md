# A-share Full-Year Coverage Plan

- Status: `PARTIAL_STALE_FULL_CROSS_SECTION_CACHE`
- Answer: `NO` — current past-year full A-share records are not considered materialized unless status is `MATERIALIZED_CURRENT_FULL_YEAR_CANDIDATE`.
- Target: `2025-07-13` to `2026-07-13`
- Current cache range: `20230901` to `20240731`
- Current daily files: `220`
- Stock basic rows: `5865`
- Total cached daily rows: `1172054`
- Current A-share strategy cases: `76`
- Ranking gate approved: `0`

## Blockers

- `daily_cache_ends_before_target_end`
- `daily_cache_is_stale_for_current_past_year`

## Overnight OpenClaw Plan

- Owner: `stock-agent`
- Mode: `bounded_read_or_simulation_only`
- Batch size: `20` trade dates
- Estimated batches: `13`
- Stop on non-zero exit, row-count anomaly, hash/date mismatch, secret exposure, broker/webhook/order attempt.

## Safety

- Simulation only.
- No broker API.
- No order placement.
- No trading webhook.
- No user-facing ranking impact from this plan.

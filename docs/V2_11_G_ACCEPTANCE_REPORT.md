# V2.11-G Acceptance Report

Acceptance target: `V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run`

Purpose: run the V2.11-F A-share rebuild proposals through a larger Tushare
historical-cache sample before any A-share idea can re-enter a user-facing
simulation action packet.

## Expected Evidence

- `data/reports/V2_11_G_A_SHARE_REBUILT_CANDIDATE_SANDBOX_DRY_RUN_PASS.marker`
- `data/reports/v2_11_g_a_share_rebuilt_candidate_sandbox_dry_run_latest.json`
- `data/reports/v2_11_g_a_share_rebuilt_candidate_sandbox_dry_run_latest.md`
- `data/processed/v2_11_g_acceptance/<run_id>/a_share_rebuilt_expanded_cases.jsonl`
- `data/processed/v2_11_g_acceptance/<run_id>/a_share_rebuilt_candidate_sandbox_report.json`

## Acceptance Meaning

`V2.11-G PASS` means the rebuilt A-share proposals were tested on an expanded
historical sample and Aegis made an evidence-based reentry decision. If no
rebuilt strategy passes, A-share remains blocked.

This stage is not a buy list, not an order, and not live advice.

## Safety Boundary

- Simulation-only.
- Expanded historical sandbox only.
- No real trade.
- No broker API.
- No trading webhook.
- No order placement.
- No live price.
- No position size.
- No secret storage.
- No production Recommendation/PaperTrade/Review/Memory mutation.
- Dashboard Contract unchanged.

## Next

If the expanded sandbox produces zero passing rebuilt A-share strategies,
refresh the user-facing brief so the block is visible and understandable.

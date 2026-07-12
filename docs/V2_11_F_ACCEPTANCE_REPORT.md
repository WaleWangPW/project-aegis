# V2.11-F Acceptance Report

Acceptance target: `V2.11-F A-Share Tushare Strategy Candidate Rebuild`

Purpose: turn failed Tushare-backed A-share sandbox evidence into a bounded
research rebuild queue. This stage does not approve A-share suggestions. It
keeps A-share blocked until a rebuilt candidate passes a later sandbox and
Suggestion Gate.

## Expected Evidence

- `data/reports/V2_11_F_A_SHARE_TUSHARE_STRATEGY_CANDIDATE_REBUILD_PASS.marker`
- `data/reports/v2_11_f_a_share_tushare_strategy_candidate_rebuild_latest.json`
- `data/reports/v2_11_f_a_share_tushare_strategy_candidate_rebuild_latest.md`
- `data/processed/v2_11_f_acceptance/<run_id>/a_share_tushare_rebuild_proposals.json`
- `data/processed/v2_11_f_acceptance/<run_id>/a_share_tushare_strategy_candidate_rebuild_report.json`

## Acceptance Meaning

`V2.11-F PASS` means the system can explain how failed A-share strategies should
be rebuilt and retested. It is not a buy list, not an order, and not live advice.

The accepted behavior is:

- one rebuild proposal per blocked Tushare-backed A-share strategy;
- every proposal is `research_rebuild_only`;
- every proposal requires a later historical sandbox and Suggestion Gate;
- zero user-facing A-share suggestions are produced;
- no strategy is auto-applied.

## Safety Boundary

- Simulation-only.
- Manual external execution only.
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

`V2.11-G A-Share Rebuilt Candidate Sandbox Dry Run`: run the rebuilt proposals
through a larger historical sample before any A-share candidate can re-enter a
usable simulation action packet.

# V2.9-I User Returned Evidence Refresh

- status: `PASS`
- run_id: `v2_9_i_20260711_acceptance`
- accepted_returned_evidence_count: `1`
- blocked_returned_evidence_count: `1`
- refreshed_review_count: `1`
- review_resolved_count: `1`

## Boundary

- 只写验收目录下的 refreshed simulation records。
- actual_return 只能来自用户回传证据，不由 Aegis 编造。
- 不写生产 reviews.jsonl / memory.jsonl / investment_memory.jsonl。
- 不写生产 paper_trades.jsonl 或 recommendations.jsonl。
- 不接 Broker API，不用 webhook，不自动下单。

## Refreshed Queue

### ptr_virtual_pending_entry_packet_paper_intake_packet_fb_watch_001

- outcome: `success`
- decision_quality: `reasonable_decision`
- actual_return: `0.012`
- actual_return_source: `user_returned_evidence`

# V2.6-C Feedback To Review/Memory Bridge

- status: `PASS`
- run_id: `v2_6_c_20260711_acceptance`
- review_link_count: `2`
- memory_candidate_count: `2`

## Boundary

- 只生成复盘证据链接和记忆候选。
- 不写 reviews.jsonl。
- 不写 memory.jsonl。
- 不改 PaperTrade 或 RecommendationRecord。
- 不做真实交易、不接 Broker API、不使用 webhook。

## feedback_memory_candidate_fb_v2_6_b_001

- symbol: `600036.SH`
- feedback_id: `fb_v2_6_b_001`
- requires_review_before_memory_write: `True`
- lesson: 600036.SH（A）：用户回传 `manual_watch` 反馈，可作为后续复盘上下文，但不能自动改变策略或交易状态。

## feedback_memory_candidate_fb_v2_6_b_002

- symbol: `00700.HK`
- feedback_id: `fb_v2_6_b_002`
- requires_review_before_memory_write: `True`
- lesson: 00700.HK（H）：用户回传 `external_manual_execution` 反馈，可作为后续复盘上下文，但不能自动改变策略或交易状态。

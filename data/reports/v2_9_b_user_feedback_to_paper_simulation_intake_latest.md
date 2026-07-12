# V2.9-B User Feedback To Paper Simulation Intake

- status: `PASS`
- run_id: `v2_9_b_20260711_acceptance`
- feedback_count: `5`
- accepted_count: `3`
- blocked_count: `2`
- paper_simulation_intake_count: `2`

## Boundary

- 只接收用户对 V2.9-A 决策包的反馈证据。
- 只生成 paper simulation intake candidates。
- 不写 PaperTrade。
- 不写 RecommendationRecord。
- 不接 Broker API，不用 webhook，不自动下单。

## 600519.SH

- feedback_id: `packet_fb_watch_001`
- intake_action: `paper_watch_candidate`
- requires_user_price_before_paper_trade: `True`

## 601398.SH

- feedback_id: `packet_fb_external_003`
- intake_action: `manual_external_action_evidence`
- requires_user_price_before_paper_trade: `True`

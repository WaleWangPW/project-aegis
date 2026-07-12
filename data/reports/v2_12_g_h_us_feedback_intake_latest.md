# V2.12-G H/US User Feedback Intake

- status: `PASS`
- run_id: `v2_12_g_20260712_acceptance`
- feedback_count: `5`
- accepted_count: `3`
- blocked_count: `2`
- simulation_followup_count: `2`

## Boundary

- 只接收用户对 V2.12-F H/US simulation brief 的反馈证据。
- 只生成 simulation follow-up candidates。
- 不写 PaperTrade、Recommendation、Review 或 Memory。
- 不接 Broker API，不用 webhook，不自动下单。

## H_API_SANDBOX_PAPER_BASKET

- feedback_id: `h_us_fb_watch_001`
- followup_action: `paper_watch_evidence`
- requires_user_price_before_paper_trade: `True`

## US_API_SANDBOX_PAPER_BASKET

- feedback_id: `h_us_fb_external_003`
- followup_action: `manual_external_action_evidence`
- requires_user_price_before_paper_trade: `True`

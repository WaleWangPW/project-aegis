# V2.8-F Refresh Queue Usable Brief

- status: `PASS`
- run_id: `v2_8_f_20260711_acceptance`
- candidate_count: `3`
- blocked_count: `3`
- candidate_markets: `['A', 'H', 'US']`

## Boundary

- 只展示模拟策略篮子。
- 不是具体个股买卖建议。
- 不做真实交易。
- 不接 Broker API。
- 不使用 webhook。
- 不给实时价格或仓位数量。
- 用户在 Aegis 外部自行判断并手动执行。

## Items

### A_LOW_VOL_DIVIDEND_PAPER_BASKET

- market: `A`
- status: `candidate`
- action: `review_for_simulated_strategy_watch`
- summary: A_LOW_VOL_DIVIDEND_PAPER_BASKET (A) 是通过历史沙盘和 Suggestion Gate 的模拟策略篮子，只适合进入观察/纸面验证，不是具体个股买入指令。
- blocked_by: `none`
- evidence_refs: `5`

### A_VALUE_QUALITY_PAPER_BASKET

- market: `A`
- status: `blocked`
- action: `do_not_use_for_entry`
- summary: A_VALUE_QUALITY_PAPER_BASKET (A) 当前被阻断，原因：strategy_sandbox_not_passed。不要用于模拟入场。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `5`

### H_LOW_VOL_DIVIDEND_PAPER_BASKET

- market: `H`
- status: `candidate`
- action: `review_for_simulated_strategy_watch`
- summary: H_LOW_VOL_DIVIDEND_PAPER_BASKET (H) 是通过历史沙盘和 Suggestion Gate 的模拟策略篮子，只适合进入观察/纸面验证，不是具体个股买入指令。
- blocked_by: `none`
- evidence_refs: `5`

### H_SMART_BETA_PAPER_BASKET

- market: `H`
- status: `blocked`
- action: `do_not_use_for_entry`
- summary: H_SMART_BETA_PAPER_BASKET (H) 当前被阻断，原因：strategy_sandbox_not_passed。不要用于模拟入场。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `5`

### US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET

- market: `US`
- status: `blocked`
- action: `do_not_use_for_entry`
- summary: US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET (US) 当前被阻断，原因：strategy_sandbox_not_passed。不要用于模拟入场。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `5`

### US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET

- market: `US`
- status: `candidate`
- action: `review_for_simulated_strategy_watch`
- summary: US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET (US) 是通过历史沙盘和 Suggestion Gate 的模拟策略篮子，只适合进入观察/纸面验证，不是具体个股买入指令。
- blocked_by: `none`
- evidence_refs: `5`

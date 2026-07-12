# V2.6-A Usable Suggestion Brief

- status: `PASS`
- run_id: `v2_6_a_20260711_acceptance_cn`
- candidate_count: `3`
- blocked_count: `3`
- candidate_markets: `['A', 'H', 'US']`

## Boundary

- 仅模拟建议。
- 不做真实交易。
- 不接 Broker API。
- 不使用 webhook。
- 不给实时价格或仓位数量。
- 用户在 Aegis 外部自行判断并手动执行。

## Candidates

### 600036.SH - 招商银行

- market: `A`
- status: `candidate`
- action: `review_for_simulated_paper_entry`
- source: `api_fixture_candidate_refresh`
- summary: 600036.SH (A) 是基于已批准证据生成的模拟候选。请先查看证据和风险，再由你在外部软件中自行决定是否手动操作。
- blocked_by: `none`
- evidence_refs: `9`

### A_VALUE_QUALITY_PAPER_BASKET

- market: `A`
- status: `blocked`
- action: `do_not_use_for_entry`
- source: `none`
- summary: 这条策略路径已被阻断，不能作为可用入场候选。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `8`

### 00700.HK - Tencent Holdings

- market: `H`
- status: `candidate`
- action: `review_for_simulated_paper_entry`
- source: `api_fixture_candidate_refresh`
- summary: 00700.HK (H) 是基于已批准证据生成的模拟候选。请先查看证据和风险，再由你在外部软件中自行决定是否手动操作。
- blocked_by: `none`
- evidence_refs: `9`

### H_SMART_BETA_PAPER_BASKET

- market: `H`
- status: `blocked`
- action: `do_not_use_for_entry`
- source: `none`
- summary: 这条策略路径已被阻断，不能作为可用入场候选。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `8`

### US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET

- market: `US`
- status: `blocked`
- action: `do_not_use_for_entry`
- source: `none`
- summary: 这条策略路径已被阻断，不能作为可用入场候选。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `8`

### MSFT - Microsoft

- market: `US`
- status: `candidate`
- action: `review_for_simulated_paper_entry`
- source: `api_fixture_candidate_refresh`
- summary: MSFT (US) 是基于已批准证据生成的模拟候选。请先查看证据和风险，再由你在外部软件中自行决定是否手动操作。
- blocked_by: `none`
- evidence_refs: `9`

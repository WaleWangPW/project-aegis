# Project Aegis Simulation Action Packet

- status: `PASS`
- target: `V2.11-A Simulation Suggestion Action Packet`
- today_focus_count: `6`
- blocked_count: `3`
- api_backed_brief_status: `blocked_missing_real_api_artifacts`

## Today Focus

### 1. 600519.SH - 贵州茅台

- market: `A`
- action_type: `manual_review_for_simulation_watch`
- source_mode: `approved_fixture_not_live_market_data`
- candidate_score: `0.95`
- evidence_ref_count: `9`
- user_steps:
  - 在外部行情软件核对实时价格、公告、新闻和流动性。
  - 检查是否与当前持仓、现金计划和个人风险预算冲突。
  - 如果你决定手动操作，只能在 Aegis 外部完成，并把截图或文字结果回传。

### 2. 600036.SH - 招商银行

- market: `A`
- action_type: `manual_review_for_simulation_watch`
- source_mode: `approved_fixture_not_live_market_data`
- candidate_score: `0.85`
- evidence_ref_count: `9`
- user_steps:
  - 在外部行情软件核对实时价格、公告、新闻和流动性。
  - 检查是否与当前持仓、现金计划和个人风险预算冲突。
  - 如果你决定手动操作，只能在 Aegis 外部完成，并把截图或文字结果回传。

### 3. 00700.HK - Tencent Holdings

- market: `H`
- action_type: `manual_review_for_simulation_watch`
- source_mode: `approved_fixture_not_live_market_data`
- candidate_score: `0.82`
- evidence_ref_count: `9`
- user_steps:
  - 在外部行情软件核对实时价格、公告、新闻和流动性。
  - 检查是否与当前持仓、现金计划和个人风险预算冲突。
  - 如果你决定手动操作，只能在 Aegis 外部完成，并把截图或文字结果回传。

### 4. 00005.HK - HSBC Holdings

- market: `H`
- action_type: `manual_review_for_simulation_watch`
- source_mode: `approved_fixture_not_live_market_data`
- candidate_score: `0.74`
- evidence_ref_count: `9`
- user_steps:
  - 在外部行情软件核对实时价格、公告、新闻和流动性。
  - 检查是否与当前持仓、现金计划和个人风险预算冲突。
  - 如果你决定手动操作，只能在 Aegis 外部完成，并把截图或文字结果回传。

### 5. CRCL - Circle Internet Group

- market: `US`
- action_type: `manual_review_for_simulation_watch`
- source_mode: `approved_fixture_not_live_market_data`
- candidate_score: `0.78`
- evidence_ref_count: `9`
- user_steps:
  - 在外部行情软件核对实时价格、公告、新闻和流动性。
  - 检查是否与当前持仓、现金计划和个人风险预算冲突。
  - 如果你决定手动操作，只能在 Aegis 外部完成，并把截图或文字结果回传。

### 6. MSFT - Microsoft

- market: `US`
- action_type: `manual_review_for_simulation_watch`
- source_mode: `approved_fixture_not_live_market_data`
- candidate_score: `0.76`
- evidence_ref_count: `9`
- user_steps:
  - 在外部行情软件核对实时价格、公告、新闻和流动性。
  - 检查是否与当前持仓、现金计划和个人风险预算冲突。
  - 如果你决定手动操作，只能在 Aegis 外部完成，并把截图或文字结果回传。

## Do Not Use

- `A_VALUE_QUALITY_PAPER_BASKET` (A): strategy_sandbox_not_passed
- `H_SMART_BETA_PAPER_BASKET` (H): strategy_sandbox_not_passed
- `US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET` (US): strategy_sandbox_not_passed

## Return Evidence Requests

- paper_trade_id: `ptr_virtual_pending_entry_packet_paper_intake_packet_fb_watch_001`
  outcome: `pending`
  no_return_fabrication: `True`

## Boundary

- 只做模拟观察和证据整理。
- 不做真实交易。
- 不接 Broker API。
- 不使用 trading webhook。
- 不生成实时价格、仓位数量或订单。

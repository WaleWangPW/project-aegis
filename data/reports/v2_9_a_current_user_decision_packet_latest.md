# V2.9-A Current User Decision Packet

- status: `PASS`
- run_id: `v2_9_a_20260711_acceptance`
- candidate_count: `9`
- blocked_count: `3`
- candidate_markets: `['A', 'H', 'US']`
- real_user_api_status: `blocked_missing_metadata`

## 你现在可以怎么用

- 查看 simulation_candidate 项，作为人工观察和纸面验证清单。
- 在外部行情/券商软件手动核对实时价格、流动性、公司事件和持仓风险。
- 如果你决定实际操作，只能在 Aegis 外部手动下单。
- 把截图、成交记录或文字决策回传给 Aegis 作为 evidence input。

## 边界

- 不自动下单。
- 不连接 Broker API。
- 不使用 trading webhook。
- 不提供实时价格或仓位数量。
- 不把 fixture candidates 冒充为 live API candidates。

当前阻塞：真实用户 API 仍缺 config/external_api_connectors.local.json 的非敏感 metadata 和本机 env var，因此 live API-backed candidates 尚不可声明。

## 候选与阻断

### 600519.SH

- market: `A`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### 600036.SH

- market: `A`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### 601398.SH

- market: `A`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### 00700.HK

- market: `H`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### 00005.HK

- market: `H`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### 00941.HK

- market: `H`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### CRCL

- market: `US`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### MSFT

- market: `US`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### NVDA

- market: `US`
- status: `simulation_candidate`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- blocked_by: `none`
- evidence_refs: `9`

### A_VALUE_QUALITY_PAPER_BASKET

- market: `A`
- status: `blocked`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 不要用于模拟入场；先解决阻断原因：strategy_sandbox_not_passed。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `8`

### H_SMART_BETA_PAPER_BASKET

- market: `H`
- status: `blocked`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 不要用于模拟入场；先解决阻断原因：strategy_sandbox_not_passed。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `8`

### US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET

- market: `US`
- status: `blocked`
- source_mode: `approved_fixture_not_live_market_data`
- user_action: 不要用于模拟入场；先解决阻断原因：strategy_sandbox_not_passed。
- blocked_by: `strategy_sandbox_not_passed`
- evidence_refs: `8`

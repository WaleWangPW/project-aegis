# Project Aegis 当前目标能力包

- 状态：`PASS`
- 阶段：`V2.10-A Current Objective Capability Pack`
- 联网/API：`partial_ready_waiting_user_api`
- 历史沙盘：`ready_simulation_only`
- 策略研究：`ready_summary_only_requires_sandbox_before_suggestion`
- 可用建议：`ready_simulation_only_manual_execution`

## 四项目标状态

### 可以联网读取

- 当前状态：`partial_ready_waiting_user_api`
- 阻塞：`config/external_api_connectors.local.json and local env var are still required for real user API reads.`
- public_source_attempted_count: `12`
- public_source_reachable_count: `8`
- public_source_status_counts: `{'fetch_error': 4, 'reachable': 8}`
- real_user_api_status: `blocked_missing_metadata`

### 可以根据历史记录做模拟沙盘

- 当前状态：`ready_simulation_only`
- 阻塞：`None`
- historical_case_count: `24`
- pass_count: `3`
- fail_count: `3`
- passing_strategies: `['strategy_a_low_vol_dividend_defensive', 'strategy_h_low_vol_dividend', 'strategy_us_value_quality_momentum']`
- failing_strategies: `['strategy_a_value_quality_multifactor', 'strategy_h_smart_beta_multifactor', 'strategy_us_low_vol_risk_overlay']`

### 深度搜索国内外 A股/美股/港股选股策略

- 当前状态：`ready_summary_only_requires_sandbox_before_suggestion`
- 阻塞：`None`
- source_record_count: `12`
- market_coverage: `{'A': 4, 'GLOBAL': 6, 'H': 2, 'US': 6}`
- strategy_family_coverage: `{'dividend': 6, 'low_volatility': 8, 'momentum': 7, 'multi_factor': 7, 'quality': 9, 'risk_overlay': 3, 'size': 6, 'value': 10}`
- publisher_coverage: `{'AQR / Financial Analysts Journal': 1, 'Fama and French': 1, 'Hang Seng Indexes': 1, 'Kenneth R. French Data Library': 1, 'MSCI': 3, 'PanAgora / CAIA': 1, 'Research Affiliates': 1, 'S&P Dow Jones Indices': 3}`

### 有建议可以产生给用户使用

- 当前状态：`ready_simulation_only_manual_execution`
- 阻塞：`Live API-backed candidates remain unavailable until user metadata/env var are provided.`
- candidate_count: `9`
- blocked_count: `3`
- candidate_markets: `['A', 'H', 'US']`
- top_candidate_symbols: `['600519.SH', '600036.SH', '00700.HK', 'CRCL', 'MSFT', '00005.HK']`
- real_user_api_status: `blocked_missing_metadata`

## 当前可用模拟候选

### 600519.SH 贵州茅台

- 市场：`A`
- 策略：`strategy_a_low_vol_dividend_defensive`
- 分数：`0.95`
- 来源：`approved_fixture_not_live_market_data`
- 用户动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。

### 600036.SH 招商银行

- 市场：`A`
- 策略：`strategy_a_low_vol_dividend_defensive`
- 分数：`0.85`
- 来源：`approved_fixture_not_live_market_data`
- 用户动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。

### 00700.HK Tencent Holdings

- 市场：`H`
- 策略：`strategy_h_low_vol_dividend`
- 分数：`0.82`
- 来源：`approved_fixture_not_live_market_data`
- 用户动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。

### CRCL Circle Internet Group

- 市场：`US`
- 策略：`strategy_us_value_quality_momentum`
- 分数：`0.78`
- 来源：`approved_fixture_not_live_market_data`
- 用户动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。

### MSFT Microsoft

- 市场：`US`
- 策略：`strategy_us_value_quality_momentum`
- 分数：`0.76`
- 来源：`approved_fixture_not_live_market_data`
- 用户动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。

### 00005.HK HSBC Holdings

- 市场：`H`
- 策略：`strategy_h_low_vol_dividend`
- 分数：`0.74`
- 来源：`approved_fixture_not_live_market_data`
- 用户动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。

## 用户下一步
- Read the simulation-only candidates as a watch and paper-verification list.
- Manually verify live prices, events, position conflicts, and personal risk budget outside Aegis.
- If you act externally, return screenshots/text/outcome evidence through config/user_returned_evidence.local.json.
- Provide non-secret API connector metadata and a local env var when ready to replace fixture candidate sources with real API-backed reads.

## 安全边界

- 只做 simulation-only 建议和纸面验证。
- 不真实下单。
- 不连接 Broker API。
- 不使用 trading webhook。
- 不给实时价格或仓位数量。
- 不把 fixture candidates 冒充为 live API candidates。

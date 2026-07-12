# Project Aegis 当前可用模拟简报

- 状态：`PASS`
- 阶段：`V2.9-H Current Usable Simulation Brief Refresh`
- 候选数量：`9`
- 阻断路径：`3`
- 覆盖市场：`['A', 'H', 'US']`
- 真实 API 状态：`blocked_missing_metadata`

## 现在能做什么

- 系统已有 bounded API/live-public-source 读取入口和公开来源 hash 审计能力；真实用户 API 仍等待非敏感 metadata 与本机 env var。
- 已完成 A/H/US refresh hypotheses 的历史沙盘重跑；当前可见 pass/fail 证据，但通过项仍只允许进入 simulation-only suggestion path。
- A股、港股、美股策略研究已进入 source catalog、sandbox queue、Suggestion Gate、concrete candidate binding 和当前 decision packet。
- 当前可输出 simulation-only 候选简报；用户若采用，必须在外部软件手动核对和执行，再把截图或文字回传给 Aegis。

## 你可以怎么用

- 阅读当前 simulation candidates，作为观察和纸面验证清单。
- 在外部行情/券商软件手动核对实时价格、事件、持仓冲突和个人风险预算。
- 把截图、成交记录或文字决策回传给 Aegis 作为证据。

## 不能做什么

- Aegis 不真实下单。
- Aegis 不连接 Broker API。
- Aegis 不使用 trading webhook。
- Aegis 不给实时价格或仓位数量。
- Aegis 不把 fixture candidates 冒充为 live API candidates。

当前阻塞：真实用户 API 仍缺 config/external_api_connectors.local.json 的非敏感 metadata 和本机 env var，因此 live API-backed candidates 尚不可声明。

## 重点模拟候选

### 600519.SH 贵州茅台

- 市场：`A`
- 策略：`strategy_a_low_vol_dividend_defensive`
- 分数：`0.95`
- 来源：`approved_fixture_not_live_market_data`
- 建议动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- 证据数：`9`

### 600036.SH 招商银行

- 市场：`A`
- 策略：`strategy_a_low_vol_dividend_defensive`
- 分数：`0.85`
- 来源：`approved_fixture_not_live_market_data`
- 建议动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- 证据数：`9`

### 00700.HK Tencent Holdings

- 市场：`H`
- 策略：`strategy_h_low_vol_dividend`
- 分数：`0.82`
- 来源：`approved_fixture_not_live_market_data`
- 建议动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- 证据数：`9`

### CRCL Circle Internet Group

- 市场：`US`
- 策略：`strategy_us_value_quality_momentum`
- 分数：`0.78`
- 来源：`approved_fixture_not_live_market_data`
- 建议动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- 证据数：`9`

### MSFT Microsoft

- 市场：`US`
- 策略：`strategy_us_value_quality_momentum`
- 分数：`0.76`
- 来源：`approved_fixture_not_live_market_data`
- 建议动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- 证据数：`9`

### 00005.HK HSBC Holdings

- 市场：`H`
- 策略：`strategy_h_low_vol_dividend`
- 分数：`0.74`
- 来源：`approved_fixture_not_live_market_data`
- 建议动作：加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。
- 证据数：`9`

## 当前复盘/记忆队列

### ptr_virtual_pending_entry_packet_paper_intake_packet_fb_watch_001

- review_id：`rev_virtual_ptr_virtual_pending_entry_packet_paper_intake_packet_fb_watch_001_entry`
- outcome：`pending`
- decision_quality：`unclear`
- actual_return：`None`
- 说明：600519.SH（A）已进入 simulation-only virtual PaperTrade 复盘队列；当前尚无 forward return，因此复盘结果保持 pending/unclear。

## 阻断路径

- `A_VALUE_QUALITY_PAPER_BASKET` / `A` blocked_by=`strategy_sandbox_not_passed`
- `H_SMART_BETA_PAPER_BASKET` / `H` blocked_by=`strategy_sandbox_not_passed`
- `US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET` / `US` blocked_by=`strategy_sandbox_not_passed`

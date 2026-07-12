# Project Aegis H/US 当前模拟建议简报

- 状态：`PASS`
- 阶段：`V2.12-F H-US Current Usable Simulation Brief Refresh`
- 候选数量：`2`
- 覆盖市场：`['H', 'US']`
- 真实交易允许：`False`

## 现在能做什么

- EODHD/Twelve Data/Tushare 等用户 API 已有 secret-safe probe、metadata gate、bounded cache readiness 和沙盘证据链；本简报复用已验收证据，不重新联网。
- H/US normalized cache samples 已进入历史沙盘；当前只证明小样本纸面验证通过，不能证明生产策略稳定有效。
- A/H/US 策略研究已具备 source catalog、sandbox、Suggestion Gate 和 H/US API-backed simulation draft 链路。
- 当前可给出 H/US simulation-only 观察候选；用户必须在外部软件自行核对和手动执行，再把截图或文字反馈回传给 Aegis。

## 你可以怎么用

- 把候选加入模拟观察清单。
- 在外部行情/券商软件手动核对实时价格、新闻事件、持仓冲突和个人风险预算。
- 把截图、成交记录或文字判断回传给 Aegis，作为后续模拟复盘证据。

## 不能做什么

- Aegis 不真实下单。
- Aegis 不连接 Broker API。
- Aegis 不使用 trading webhook。
- Aegis 不给实时价格。
- Aegis 不给仓位数量。
- Aegis 不把小样本 sandbox PASS 解释成正式策略通过。

## H/US 模拟候选

### H_API_SANDBOX_PAPER_BASKET

- 市场：`H`
- 状态：`simulation_candidate`
- 动作：加入模拟观察清单；如你感兴趣，只能在外部软件手动核对实时价格、事件和风险，再决定是否做纸面记录。
- 历史样本：`00700.HK`
- 样本数：`1`
- win_rate：`1.0000`
- average_return：`0.1130`
- max_drawdown：`-0.0112`
- 说明：H_API_SANDBOX_PAPER_BASKET 是基于 V2.12-D/V2.12-E 证据生成的 H/US 模拟候选篮子。它可用于观察和纸面验证，但不是实盘买卖建议。
- 证据数：`3`

### US_API_SANDBOX_PAPER_BASKET

- 市场：`US`
- 状态：`simulation_candidate`
- 动作：加入模拟观察清单；如你感兴趣，只能在外部软件手动核对实时价格、事件和风险，再决定是否做纸面记录。
- 历史样本：`AAPL.US`
- 样本数：`2`
- win_rate：`1.0000`
- average_return：`0.0365`
- max_drawdown：`-0.0181`
- 说明：US_API_SANDBOX_PAPER_BASKET 是基于 V2.12-D/V2.12-E 证据生成的 H/US 模拟候选篮子。它可用于观察和纸面验证，但不是实盘买卖建议。
- 证据数：`4`

## 边界

- 仅模拟。
- 不是实盘建议。
- 不含实时价格。
- 不含仓位数量。
- 不接券商。
- 不下单。

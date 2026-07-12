# Project Aegis Finnhub Quote 当前模拟建议简报

- 状态：`PASS`
- 阶段：`V2.13-I Finnhub Quote Current Simulation Brief`
- 候选数量：`1`
- 候选标的：`['AAPL.US']`
- social_sentiment_status：`blocked_plan_or_rate_limit`
- 真实交易允许：`False`

## 现在能做什么

- Finnhub quote 已通过 secret-safe live probe 和 cache-readiness；本简报复用已验收的 V2.13-H gate evidence，不重新联网。
- AAPL.US quote-context candidate 已在 8 个 historical cases 上通过 sandbox，并经过 Suggestion Gate。
- 该候选只证明 Finnhub quote-context 证据链可以进入模拟观察；social sentiment 仍 blocked，不能作为 Reddit/Twitter 情绪信号。
- 当前可给出 1 条 AAPL.US simulation-only 观察候选；用户必须在外部软件自行核对并手动决策，再把截图或文字反馈回传给 Aegis。

## 你可以怎么用

- 把 AAPL.US 加入模拟观察清单。
- 在外部行情或券商软件手动核对实时价格、公告、新闻事件、持仓冲突和个人风险预算。
- 如果你手动做了模拟或真实外部动作，可把截图、价格、日期和文字判断回传给 Aegis 做复盘证据。

## 不能做什么

- Aegis 不真实下单。
- Aegis 不连接 Broker API。
- Aegis 不使用 trading webhook。
- Aegis 不给实时价格。
- Aegis 不给仓位数量。
- Aegis 不使用 Finnhub social sentiment 作为信号。
- Aegis 不把小样本 sandbox PASS 解释成正式策略稳定通过。

## 模拟候选

### AAPL.US

- 市场：`US`
- 状态：`simulation_candidate`
- 动作：可加入模拟观察清单；如果你感兴趣，只能在外部软件手动核对实时价格、公告、新闻、持仓冲突和个人风险预算，再决定是否记录一笔纸面模拟。
- 历史样本：`AAPL.US`
- 样本数：`8`
- win_rate：`0.6250`
- average_return：`0.0091`
- max_drawdown：`-0.0484`
- social_sentiment_status：`blocked_plan_or_rate_limit`
- 说明：AAPL.US 是 Finnhub quote-context 证据链经过历史沙盘和 Suggestion Gate 后形成的模拟观察候选。它不是实盘买卖建议，也不包含实时价格或仓位。
- 证据数：`4`

## 边界

- 仅模拟。
- 不是实盘建议。
- 不含实时价格。
- 不含仓位数量。
- 不接券商。
- 不下单。
- 不使用 Finnhub social sentiment。

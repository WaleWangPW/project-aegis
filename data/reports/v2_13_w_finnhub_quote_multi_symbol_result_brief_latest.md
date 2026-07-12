# Project Aegis 多股票沙盘阻断简报

- 状态：`PASS`
- 阶段：`V2.13-W Finnhub Quote Multi-Symbol Sandbox Result Brief`
- 阻断数量：`3`
- 通过数量：`0`
- 阻断标的：`['CRCL.US', 'MSFT.US', 'NVDA.US']`
- suggestion_gate_ready：`False`
- user_facing_suggestion_allowed：`False`

## 当前结论

- Finnhub quote 和 EODHD historical bars 已完成联网读取并形成证据链。
- 本轮 3 个多股票候选已完成 81 个 historical cases 的 sandbox evaluation。
- 本轮没有可用建议：3 个候选全部未通过沙盘，不能进入 Suggestion Gate。
- 失败原因已结构化保存，可用于后续重新筛选或调整策略假设。

## 阻断明细

### CRCL.US

- 状态：`blocked_by_sandbox`
- 动作：不要把这个候选作为当前模拟建议使用；等待重新筛选、重新设定策略或更多证据。
- 样本数：`27`
- 胜率：`0.37037037037037035`
- 平均收益：`-0.015221498572253377`
- 最大回撤：`-0.17693522906793036`
- 失败原因：`['历史胜率低于通过阈值', '历史平均收益低于通过阈值', '历史最大回撤超过允许底线']`
- 说明：CRCL.US 已完成联网 quote context、历史案例组装和 sandbox evaluation，但本轮沙盘没有通过。因此它不能进入 Suggestion Gate，也不能生成用户可执行建议。

### MSFT.US

- 状态：`blocked_by_sandbox`
- 动作：不要把这个候选作为当前模拟建议使用；等待重新筛选、重新设定策略或更多证据。
- 样本数：`27`
- 胜率：`0.4444444444444444`
- 平均收益：`-0.006348927822844228`
- 最大回撤：`-0.04702791109204496`
- 失败原因：`['历史胜率低于通过阈值', '历史平均收益低于通过阈值']`
- 说明：MSFT.US 已完成联网 quote context、历史案例组装和 sandbox evaluation，但本轮沙盘没有通过。因此它不能进入 Suggestion Gate，也不能生成用户可执行建议。

### NVDA.US

- 状态：`blocked_by_sandbox`
- 动作：不要把这个候选作为当前模拟建议使用；等待重新筛选、重新设定策略或更多证据。
- 样本数：`27`
- 胜率：`0.4444444444444444`
- 平均收益：`-0.001959098221603719`
- 最大回撤：`-0.06553553461995787`
- 失败原因：`['历史胜率低于通过阈值', '历史平均收益低于通过阈值']`
- 说明：NVDA.US 已完成联网 quote context、历史案例组装和 sandbox evaluation，但本轮沙盘没有通过。因此它不能进入 Suggestion Gate，也不能生成用户可执行建议。

## 边界

- 这是阻断简报，不是建议。
- 不进入 Suggestion Gate。
- 不含实时价格。
- 不含仓位数量。
- 不接券商。
- 不下单。

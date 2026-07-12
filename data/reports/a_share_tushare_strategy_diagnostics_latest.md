# A-share Tushare Strategy Diagnostics

- Status: `PASS`
- Generated At: `2026-07-12T23:10:41+08:00`
- A-share Cases: `62`
- Rankable Strategies: `0`
- Feature Gaps: `1`
- Deep Sandbox Fail: `5`
- Boundary: diagnostic only; no ranking impact, no broker, no order, no trading webhook.

## Priority Actions

- **龙虎榜/游资席位**: `collect_endpoint_history` - 当前 historical cases 对这些 endpoint 没有足够覆盖，不能判断策略可行性。
- **机构持仓稳定**: `tighten_signal_definition` - 信号太宽，几乎什么都能命中但胜率低，应增加趋势/估值/回撤过滤。
- **治理/高管激励**: `tighten_signal_definition` - 信号太宽，几乎什么都能命中但胜率低，应增加趋势/估值/回撤过滤。
- **主力资金流向**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。
- **因子+流动性质量**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。
- **股东人数/筹码集中**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。

## Deep Diagnostics

| Strategy | Signal Cases | Win Rate | Avg Return | Max Drawdown | Action |
| --- | ---: | ---: | ---: | ---: | --- |
| 主力资金流向 | 15 | 26.7% | -10.6% | -49.3% | add_risk_veto_before_retest |
| 机构持仓稳定 | 30 | 20.0% | -8.3% | -49.3% | tighten_signal_definition |
| 股东人数/筹码集中 | 21 | 28.6% | -4.9% | -25.0% | add_risk_veto_before_retest |
| 因子+流动性质量 | 37 | 24.3% | -7.0% | -40.9% | add_risk_veto_before_retest |
| 治理/高管激励 | 40 | 27.5% | -6.2% | -49.3% | tighten_signal_definition |

# A-share Tushare Strategy Diagnostics

- Status: `PASS`
- Generated At: `2026-07-13T01:47:00+08:00`
- A-share Cases: `76`
- Rankable Strategies: `0`
- Feature Gaps: `0`
- Deep Sandbox Fail: `5`
- Boundary: diagnostic only; no ranking impact, no broker, no order, no trading webhook.

## Priority Actions

- **机构持仓稳定**: `tighten_signal_definition` - 信号太宽，几乎什么都能命中但胜率低，应增加趋势/估值/回撤过滤。
- **治理/高管激励**: `tighten_signal_definition` - 信号太宽，几乎什么都能命中但胜率低，应增加趋势/估值/回撤过滤。
- **主力资金流向**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。
- **因子+流动性质量**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。

## Deep Diagnostics

| Strategy | Signal Cases | Win Rate | Avg Return | Max Drawdown | Action |
| --- | ---: | ---: | ---: | ---: | --- |
| 主力资金流向 | 16 | 25.0% | -11.8% | -49.3% | add_risk_veto_before_retest |
| 机构持仓稳定 | 30 | 20.0% | -8.3% | -49.3% | tighten_signal_definition |
| 股东人数/筹码集中 | 16 | 31.2% | -5.3% | -20.4% | rework_hypothesis |
| 因子+流动性质量 | 42 | 31.0% | -7.4% | -40.9% | add_risk_veto_before_retest |
| 治理/高管激励 | 40 | 27.5% | -6.2% | -49.3% | tighten_signal_definition |

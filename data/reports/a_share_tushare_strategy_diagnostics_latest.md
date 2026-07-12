# A-share Tushare Strategy Diagnostics

- Status: `PASS`
- Generated At: `2026-07-13T00:19:30+08:00`
- A-share Cases: `76`
- Rankable Strategies: `0`
- Feature Gaps: `0`
- Deep Sandbox Fail: `3`
- Boundary: diagnostic only; no ranking impact, no broker, no order, no trading webhook.

## Priority Actions

- **机构持仓稳定**: `tighten_signal_definition` - 信号太宽，几乎什么都能命中但胜率低，应增加趋势/估值/回撤过滤。
- **治理/高管激励**: `tighten_signal_definition` - 信号太宽，几乎什么都能命中但胜率低，应增加趋势/估值/回撤过滤。

## Deep Diagnostics

| Strategy | Signal Cases | Win Rate | Avg Return | Max Drawdown | Action |
| --- | ---: | ---: | ---: | ---: | --- |
| 机构持仓稳定 | 30 | 20.0% | -8.3% | -49.3% | tighten_signal_definition |
| 股东人数/筹码集中 | 16 | 31.2% | -5.3% | -20.4% | rework_hypothesis |
| 治理/高管激励 | 40 | 27.5% | -6.2% | -49.3% | tighten_signal_definition |

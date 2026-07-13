# A-share Tushare Strategy Diagnostics

- Status: `PASS`
- Generated At: `2026-07-13T08:36:07+08:00`
- A-share Cases: `74`
- Rankable Strategies: `0`
- Feature Gaps: `0`
- Deep Sandbox Fail: `5`
- Boundary: diagnostic only; no ranking impact, no broker, no order, no trading webhook.

## Priority Actions

- **机构持仓稳定**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。

## Deep Diagnostics

| Strategy | Signal Cases | Win Rate | Avg Return | Max Drawdown | Action |
| --- | ---: | ---: | ---: | ---: | --- |
| 主力资金流向 | 16 | 62.5% | 1.5% | -40.6% | rework_hypothesis |
| 机构持仓稳定 | 20 | 30.0% | -0.1% | -25.6% | add_risk_veto_before_retest |
| 股东人数/筹码集中 | 16 | 56.2% | 2.0% | -28.9% | rework_hypothesis |
| 因子+流动性质量 | 38 | 50.0% | 1.8% | -31.9% | rework_hypothesis |
| 治理/高管激励 | 40 | 47.5% | 1.7% | -35.0% | rework_hypothesis |

# A-share Tushare Strategy Diagnostics

- Status: `PASS`
- Generated At: `2026-07-13T16:05:05+08:00`
- A-share Cases: `75`
- Rankable Strategies: `0`
- Feature Gaps: `0`
- Deep Sandbox Fail: `5`
- Boundary: diagnostic only; no ranking impact, no broker, no order, no trading webhook.

## Priority Actions

- **主力资金流向**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。
- **机构持仓稳定**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。
- **股东人数/筹码集中**: `add_risk_veto_before_retest` - 信号命中后平均收益为负且回撤深，应先叠加风险否决再重测。

## Deep Diagnostics

| Strategy | Signal Cases | Win Rate | Avg Return | Max Drawdown | Action |
| --- | ---: | ---: | ---: | ---: | --- |
| 主力资金流向 | 18 | 55.6% | -3.1% | -40.6% | add_risk_veto_before_retest |
| 机构持仓稳定 | 20 | 20.0% | -2.0% | -33.0% | add_risk_veto_before_retest |
| 股东人数/筹码集中 | 17 | 35.3% | -2.1% | -34.0% | add_risk_veto_before_retest |
| 因子+流动性质量 | 41 | 46.3% | 1.0% | -34.0% | rework_hypothesis |
| 治理/高管激励 | 40 | 42.5% | 0.9% | -34.0% | rework_hypothesis |

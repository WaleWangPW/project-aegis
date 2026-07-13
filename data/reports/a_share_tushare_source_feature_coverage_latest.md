# A-share Tushare Source Feature Coverage

- Status: `PASS`
- Generated At: `2026-07-13T08:32:14+08:00`
- Ready For Deep Sandbox: `5`
- Feature Gaps: `0`
- Observations: `666`
- Boundary: metadata-only; no raw payload, no broker, no order, no trading webhook.

## Hypotheses

| Hypothesis | Feature Status | Cases | Min Coverage | Required Endpoints |
| --- | --- | ---: | ---: | --- |
| `hyp_a_tushare_capital_flow_accumulation` | `READY_FOR_DEEP_SANDBOX` | 74 | 0.88 | moneyflow |
| `hyp_a_tushare_institutional_ownership_stability` | `READY_FOR_DEEP_SANDBOX` | 40 | 1.00 | top10_holders, top10_floatholders |
| `hyp_a_tushare_holder_concentration_improvement` | `READY_FOR_DEEP_SANDBOX` | 74 | 0.95 | stk_holdernumber |
| `hyp_a_tushare_factor_liquidity_quality_overlay` | `READY_FOR_DEEP_SANDBOX` | 74 | 1.00 | stk_factor, daily_basic |
| `hyp_a_tushare_governance_reward_alignment` | `READY_FOR_DEEP_SANDBOX` | 40 | 1.00 | stk_rewards |

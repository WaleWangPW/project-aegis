# A-share Tushare Source Feature Coverage

- Status: `PASS`
- Generated At: `2026-07-12T22:19:45+08:00`
- Ready For Deep Sandbox: `5`
- Feature Gaps: `1`
- Observations: `360`
- Boundary: metadata-only; no raw payload, no broker, no order, no trading webhook.

## Hypotheses

| Hypothesis | Feature Status | Cases | Min Coverage | Required Endpoints |
| --- | --- | ---: | ---: | --- |
| `hyp_a_tushare_capital_flow_accumulation` | `READY_FOR_DEEP_SANDBOX` | 40 | 1.00 | moneyflow |
| `hyp_a_tushare_dragon_tiger_seat_confirmation` | `FEATURE_GAPS` | 40 | 0.00 | top_list, top_inst |
| `hyp_a_tushare_institutional_ownership_stability` | `READY_FOR_DEEP_SANDBOX` | 40 | 1.00 | top10_holders, top10_floatholders |
| `hyp_a_tushare_holder_concentration_improvement` | `READY_FOR_DEEP_SANDBOX` | 40 | 0.90 | stk_holdernumber |
| `hyp_a_tushare_factor_liquidity_quality_overlay` | `READY_FOR_DEEP_SANDBOX` | 40 | 1.00 | stk_factor, daily_basic |
| `hyp_a_tushare_governance_reward_alignment` | `READY_FOR_DEEP_SANDBOX` | 40 | 1.00 | stk_rewards |

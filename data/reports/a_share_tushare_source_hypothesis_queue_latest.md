# A-share Tushare Source Hypothesis Queue

- Status: `PASS`
- Generated At: `2026-07-13T09:11:11+08:00`
- Source Probe Status: `PASS`
- Latest Trade Date: `20260713`
- Hypothesis Count: `5`
- Boundary: sandbox-only; no broker, no order, no trading webhook, no raw payload.

## Hypotheses

| ID | Title | Families | Metrics |
| --- | --- | --- | --- |
| `hyp_a_tushare_capital_flow_accumulation` | A-share capital-flow accumulation hypothesis | capital_flow, momentum, risk_overlay | sample_count, win_rate, average_return, max_drawdown |
| `hyp_a_tushare_institutional_ownership_stability` | A-share institutional ownership stability hypothesis | institutional_ownership, quality, risk_overlay | disclosure_lag_days, win_rate, average_return, max_drawdown |
| `hyp_a_tushare_holder_concentration_improvement` | A-share holder concentration improvement hypothesis | holder_concentration, quality, multi_factor | holder_count_change, sample_count, win_rate, average_return |
| `hyp_a_tushare_factor_liquidity_quality_overlay` | A-share factor liquidity quality overlay hypothesis | multi_factor, quality, momentum, risk_overlay | liquidity_pass_rate, win_rate, average_return, max_drawdown |
| `hyp_a_tushare_governance_reward_alignment` | A-share governance and reward-alignment hypothesis | governance, quality, risk_overlay | governance_flag_count, downgrade_rate, win_rate, average_return |

## Blocked Or Skipped Sources

| Module | Endpoint | Status | Reason |
| --- | --- | --- | --- |
| 龙虎榜 / 游资席位 | `top_list` | `EMPTY` |  |
| 龙虎榜 / 游资席位 | `top_inst` | `EMPTY` |  |
| 机构调研热度 | `stk_survey` | `ERROR` | 请指定正确的接口名 |

## Next

Run historical sandbox for these A-share source hypotheses before ranking or recommendation use.

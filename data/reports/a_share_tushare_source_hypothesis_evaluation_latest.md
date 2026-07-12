# A-share Tushare Source Hypothesis Evaluation

- Status: `PASS`
- Generated At: `2026-07-12T21:00:10+08:00`
- Hypothesis Count: `6`
- Proxy Pass: `0`
- Needs More A-share Cases: `0`
- Proxy Fail: `6`
- Boundary: proxy sandbox only; no broker, no order, no trading webhook, no ranking impact.

## Results

| Hypothesis | Disposition | Confidence | Cases | Avg Return | Reasons |
| --- | --- | --- | ---: | ---: | --- |
| `hyp_a_tushare_capital_flow_accumulation` | `proxy_fail` | `LOW_SAMPLE_PROXY` | 8 | -0.0394 | proxy_win_rate_below_threshold, proxy_average_return_below_threshold |
| `hyp_a_tushare_dragon_tiger_seat_confirmation` | `proxy_fail` | `LOW_SAMPLE_PROXY` | 8 | -0.0394 | proxy_win_rate_below_threshold, proxy_average_return_below_threshold |
| `hyp_a_tushare_institutional_ownership_stability` | `proxy_fail` | `LOW_SAMPLE_PROXY` | 8 | -0.0394 | proxy_win_rate_below_threshold, proxy_average_return_below_threshold |
| `hyp_a_tushare_holder_concentration_improvement` | `proxy_fail` | `LOW_SAMPLE_PROXY` | 8 | -0.0394 | proxy_win_rate_below_threshold, proxy_average_return_below_threshold |
| `hyp_a_tushare_factor_liquidity_quality_overlay` | `proxy_fail` | `LOW_SAMPLE_PROXY` | 8 | -0.0394 | proxy_win_rate_below_threshold, proxy_average_return_below_threshold |
| `hyp_a_tushare_governance_reward_alignment` | `proxy_fail` | `LOW_SAMPLE_PROXY` | 8 | -0.0394 | proxy_win_rate_below_threshold, proxy_average_return_below_threshold |

## Limitation

This report uses current A-share historical candidate cases as proxy evidence. Source-specific historical features such as historical moneyflow, top-list seats, holder concentration changes, and governance events still need deeper assembly before any strategy can affect ranking.

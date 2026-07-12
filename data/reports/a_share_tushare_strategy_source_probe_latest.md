# A-share Tushare Strategy Source Probe

- Status: `PASS`
- Generated At: `2026-07-12T23:24:48+08:00`
- Latest Trade Date: `20260710`
- Sample Symbol: `000001.SZ`
- Boundary: simulation research only; no broker, no order, no trading webhook.

## Summary

- endpoint_count: `10`
- pass_count: `9`
- empty_count: `0`
- blocked_count: `1`
- priority_ready_count: `6`

## Endpoints

| Module | Endpoint | Status | Rows | Notes |
| --- | --- | --- | ---: | --- |
| 主力资金流向 | `moneyflow` | `PASS` | 5194 | ts_code, trade_date, buy_sm_vol, buy_sm_amount, sell_sm_vol, sell_sm_amount |
| 龙虎榜 / 游资席位 | `top_list` | `PASS` | 98 | trade_date, ts_code, name, close, pct_change, turnover_rate |
| 龙虎榜 / 游资席位 | `top_inst` | `PASS` | 1048 | trade_date, ts_code, exalter, buy, buy_rate, sell |
| 机构持仓与股东变化 | `top10_holders` | `PASS` | 10 | ts_code, ann_date, end_date, holder_name, hold_amount, hold_ratio |
| 机构持仓与股东变化 | `top10_floatholders` | `PASS` | 10 | ts_code, ann_date, end_date, holder_name, hold_amount, hold_ratio |
| 股东人数 / 筹码集中 | `stk_holdernumber` | `PASS` | 5 | ts_code, ann_date, end_date, holder_num |
| A 股因子与日线基础池 | `stk_factor` | `PASS` | 5519 | ts_code, trade_date, close, open, high, low |
| A 股因子与日线基础池 | `daily_basic` | `PASS` | 5599 | ts_code, trade_date, close, turnover_rate, turnover_rate_f, volume_ratio |
| 高管薪酬 / 治理 | `stk_rewards` | `PASS` | 2736 | ts_code, ann_date, end_date, name, title, reward |
| 机构调研热度 | `stk_survey` | `ERROR` | 0 | 请指定正确的接口名 |

## Next

OpenClaw stock-agent should run historical sandbox only for PASS modules, starting with priority 1-2 endpoints.

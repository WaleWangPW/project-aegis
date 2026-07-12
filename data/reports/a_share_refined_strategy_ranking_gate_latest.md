# A-share Refined Strategy Ranking Gate

- Status: `PASS`
- Generated At: `2026-07-12T23:45:07+08:00`
- Reviewed: `1`
- Approved For Simulation Sort: `0`
- Blocked: `1`
- Ranking Impact Allowed: `False`
- Boundary: review only; no raw payload, no broker, no order, no trading webhook, no user-facing suggestion.

| Strategy | Gate | Cases | Symbols | Months | Max Symbol Share | Win Rate | Avg Return | Max Drawdown | Blockers |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `refined_a_moneyflow_holder_concentration` 主力资金 + 筹码集中 | `RANKING_GATE_BLOCKED` | 3 | 2 | 2 | 0.67 | 0.67 | 0.0430 | -0.1436 | ranking_gate_case_count_below_threshold, ranking_gate_unique_symbol_count_below_threshold, ranking_gate_single_symbol_concentration_too_high, ranking_gate_entry_month_coverage_below_threshold |

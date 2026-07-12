# A-share Strategy Sample Expansion Plan

- Status: `PASS`
- Generated At: `2026-07-12T23:45:07+08:00`
- Blocked Gate Items: `1`
- Expansion Tasks: `1`
- Current Samples / Events / Event Cases: `12` / `24` / `22`
- Next Lookback / Symbols / Events Per Symbol: `90` / `24` / `3`
- Boundary: planning only; no network, no recommendation, no broker, no order, no trading webhook.

## Tasks

### 主力资金 + 筹码集中 (`refined_a_moneyflow_holder_concentration`)

- Command: `.venv/bin/python scripts/collect_a_share_dragon_tiger_research_samples.py --lookback-dates 90 --forward-days 20 --max-symbols 24 --max-events-per-symbol 3`
- Shortfalls:
  - `increase_case_count`: 当前 case=3，需要扩大事件日期和每股事件数。
  - `increase_unique_symbol_coverage`: 当前唯一股票=2，需要扩大 max_symbols 并避免重复同一股票。
  - `reduce_single_symbol_concentration`: 当前最大单股占比=0.6666666666666666，需要更多不同股票的有效事件。
  - `increase_entry_month_coverage`: 当前月份=2，需要扩大 lookback_dates。

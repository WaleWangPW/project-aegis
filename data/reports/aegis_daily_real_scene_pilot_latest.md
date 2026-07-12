# Aegis Daily Real-Scene Pilot

- Status: `PASS`
- Generated At: `2026-07-12T16:43:13+08:00`
- Dashboard: `http://localhost:8080/dashboard/index.html`
- Dashboard HTTP OK: `True`
- Send Mode: `send_if_target_available`
- Stock Assistant Send: `SENT` sent=`6` failed=`0`

## Candidate Summary

- Total candidates: `30`
- Research candidates: `13`
- News enriched: `9`
- Markets passed: `['A', 'HK', 'US']`

## Case Evaluation

- Evaluated candidates: `13`
- Continue simulation research: `8`
- Watch only: `2`
- Downgraded: `3`

## Commands

- `build_stock_selection_workbench` exit_code=`0`
- `refresh_h_us_daily_bars` exit_code=`0`
- `build_strategy_specific_historical_cases` exit_code=`0`
- `evaluate_strategy_specific_cases` exit_code=`0`
- `build_stock_assistant_cards` exit_code=`0`
- `send_stock_assistant_cards` exit_code=`0`

## Safety

- Simulation/research only.
- No broker API.
- No real order placement.
- No trading webhook.
- No position sizing.
- Feedback buttons record evidence only.

## Next User Action

- Open http://localhost:8080/dashboard/index.html
- Read 今日结论 and 风险阻塞 first
- Review Top 3 candidates only
- Use stock assistant buttons to record watch / ignore / more-news feedback
- If you place any real order externally, record it manually as external evidence only

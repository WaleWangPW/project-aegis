# V2.9-C Paper Simulation Entry Prep

- status: `PASS`
- run_id: `v2_9_c_20260711_acceptance`
- pending_entry_request_count: `2`
- required_user_fields: `entry_price, entry_date`

## Boundary

- 只生成 pending virtual entry requests。
- 不写 PaperTrade。
- 不假造 entry_price。
- 不假造 entry_date。
- 不接 Broker API，不用 webhook，不自动下单。

## 600519.SH

- market: `A`
- status: `pending_user_price_date`
- missing_fields: `entry_price, entry_date`
- ready_to_create_paper_trade: `False`

## 601398.SH

- market: `A`
- status: `pending_user_price_date`
- missing_fields: `entry_price, entry_date`
- ready_to_create_paper_trade: `False`

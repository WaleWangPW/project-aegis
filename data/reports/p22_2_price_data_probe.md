# P22.2 Price Data Probe

## Tushare
- import_ok: True
- env_token_present: False
- stored_token_present: True
- pro_api_created: True

## Backtest Input
- start_date: 2026-04-10
- end_date: 2026-07-10
- selected_count: 20
- selected_symbols_head: ['600519.SH', '600036.SH', '000858.SZ', '000001.SZ', '601398.SH']

## Cache Dirs
- data/raw/prices: exists=False, file_count=0, sample=[]
- data/cache/prices: exists=False, file_count=0, sample=[]
- data/prices: exists=False, file_count=0, sample=[]

## Tushare Cases
| case | ts_code | start | end | rows | first | last | error |
|---|---|---|---|---:|---|---|---|
| dash_2026 | 600519.SH | 2026-04-10 | 2026-07-10 | 0 | None | None | None |
| compact_2026 | 600519.SH | 20260410 | 20260710 | 61 | 20260410 | 20260709 | None |
| compact_2024 | 600519.SH | 20240101 | 20240301 | 38 | 20240102 | 20240301 | None |
| benchmark_2024 | 000300.SH | 20240101 | 20240301 | 0 | None | None | None |

# V2.13-R Finnhub Quote Multi-Symbol Live Probe Dry Run

- status: `PASS`
- run_id: `v2_13_r_20260712_restarted_codex_probe`
- network_used: `True`
- case_count: `3`
- pass_count: `3`
- fail_count: `0`
- blocked_count: `0`
- passed_symbols: `['CRCL.US', 'MSFT.US', 'NVDA.US']`
- social_sentiment_status: `blocked_plan_or_rate_limit`
- next_stage: `V2.13-S Finnhub Quote Multi-Symbol Research Context Bridge`

## Results

### CRCL.US

- status: `pass`
- provider_symbol: `CRCL`
- http_status: `200`
- normalized_quote_json: `/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo/data/processed/v2_13_r_acceptance/v2_13_r_20260712_restarted_codex_probe/normalized_quote_cache/US/quote/us_crcl_finnhub_quote.json`
- normalized_quote_json_sha256: `36ccb10e3524d0971782304bf71021736ae22dba87699abfd63140babcfbe81a`
- normalized_quote_csv: `/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo/data/processed/v2_13_r_acceptance/v2_13_r_20260712_restarted_codex_probe/normalized_quote_cache/US/quote/us_crcl_finnhub_quote.csv`
- normalized_quote_csv_sha256: `0ab8900c1a56dfa733b01894937917e9416e123b4b4913aedae73d4e8f15aad3`
- blocked_by: `[]`

### MSFT.US

- status: `pass`
- provider_symbol: `MSFT`
- http_status: `200`
- normalized_quote_json: `/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo/data/processed/v2_13_r_acceptance/v2_13_r_20260712_restarted_codex_probe/normalized_quote_cache/US/quote/us_msft_finnhub_quote.json`
- normalized_quote_json_sha256: `d7cf4c9d95a2808dd1d6cf3922467659293aab751f84fa8cdbd4efaa94498181`
- normalized_quote_csv: `/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo/data/processed/v2_13_r_acceptance/v2_13_r_20260712_restarted_codex_probe/normalized_quote_cache/US/quote/us_msft_finnhub_quote.csv`
- normalized_quote_csv_sha256: `2f82198c4692c7b26ffa2e3070e33bf728a3287e09ea6d7bfe3ef1b5478fd763`
- blocked_by: `[]`

### NVDA.US

- status: `pass`
- provider_symbol: `NVDA`
- http_status: `200`
- normalized_quote_json: `/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo/data/processed/v2_13_r_acceptance/v2_13_r_20260712_restarted_codex_probe/normalized_quote_cache/US/quote/us_nvda_finnhub_quote.json`
- normalized_quote_json_sha256: `d25e4d90bec86bae1e741c2c3623a8971062d099198650f00e96de9a95f1fb71`
- normalized_quote_csv: `/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo/data/processed/v2_13_r_acceptance/v2_13_r_20260712_restarted_codex_probe/normalized_quote_cache/US/quote/us_nvda_finnhub_quote.csv`
- normalized_quote_csv_sha256: `e4291117b60a8d965b38f1fcb5f1aaf8a9e9b8341e956d94b6ab4765500f878b`
- blocked_by: `[]`

## Boundary

- This stage only probes live quotes and writes run-specific normalized artifacts.
- It does not create user-facing suggestions.
- It does not write production Recommendation, PaperTrade, Review, or Memory records.
- It does not store request URLs, raw payloads, or token values.
- It does not connect broker APIs, webhooks, or place orders.

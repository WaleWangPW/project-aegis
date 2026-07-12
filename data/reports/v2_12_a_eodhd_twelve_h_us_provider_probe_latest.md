# V2.12-A EODHD Twelve Data H-US Provider Probe

- status: `PASS`
- run_id: `v2_12_a_20260712_acceptance`
- pass_count: `3`
- fail_count: `1`
- h_us_provider_status: `{'H': ['eodhd'], 'US': ['eodhd', 'twelve_data']}`
- next_stage: `V2.12-B H-US Provider Metadata Activation`

## Results

### eodhd US AAPL.US

- status: `pass`
- env_present: `True`
- blocked_by: `[]`
- summary: `{'shape': 'list', 'rows': 2, 'has_close': True, 'first_date': '2026-07-01', 'last_date': '2026-07-02'}`

### eodhd H 0700.HK

- status: `pass`
- env_present: `True`
- blocked_by: `[]`
- summary: `{'shape': 'list', 'rows': 2, 'has_close': True, 'first_date': '2026-07-02', 'last_date': '2026-07-03'}`

### twelve_data US AAPL

- status: `pass`
- env_present: `True`
- blocked_by: `[]`
- summary: `{'shape': 'dict', 'api_status': 'ok', 'rows': 1, 'has_close': True, 'first_datetime': '2026-07-10'}`

### twelve_data H 0700

- status: `fail`
- env_present: `True`
- blocked_by: `['fetch_error']`
- summary: `{}`

## Boundary

- Provider capability probe only.
- Env var names only; no token values.
- No request URL or raw payload storage.
- No real trade, broker API, trading webhook, order placement, or production record mutation.
- Dashboard Contract unchanged.

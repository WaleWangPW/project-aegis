# V2.8-B Acceptance Report

## Result

- Target: `V2.8-B Live Public Strategy Source Audit`
- Status: `PASS`
- Run ID: `v2_8_b_20260711_acceptance`
- Acceptance command:
  - `.venv/bin/python scripts/validate_v2_8_b_live_public_strategy_source_audit.py --run-id v2_8_b_20260711_acceptance --max-sources 12`
- Exit code: `0`
- Related regression:
  - `4 passed`
  - `28 passed`

## What Passed

`V2.8-B` runs the public strategy source audit against real public URLs. It
attempts every selected source, classifies the result, records content hashes
for reachable sources, and records fetch errors instead of hiding them.

Important current state:

- Audited sources: `12`
- Attempted sources: `12`
- Reachable sources: `8`
- Fetch errors: `4`
- Network used: `true`
- Market coverage: A, H, US, GLOBAL

Fetch errors were expected and accepted only because they are explicitly
recorded as evidence. They do not permit deleting sources or claiming those
links are reachable.

## Evidence

- `data/reports/V2_8_B_LIVE_PUBLIC_STRATEGY_SOURCE_AUDIT_PASS.marker`
- `data/reports/v2_8_b_live_public_strategy_source_audit_latest.json`
- `data/reports/v2_8_b_live_public_strategy_source_audit_latest.md`
- `data/processed/v2_8_b_acceptance/v2_8_b_20260711_acceptance/live_public_strategy_source_audit.json`

SHA256:

- `720c07afff7fdfa8e8c9549fcf7e3bfad0a0978e8294e51d6856794e2f5e47e9` `aegis/strategy/source_audit.py`
- `d79ed9c72d64712c932bd9985fc633d424d12440dc9abe10134c9e7b5eaf33ae` `scripts/validate_v2_8_b_live_public_strategy_source_audit.py`
- `96483453de192b8b5837ba4e3b504ba137c620853ff15163eb4e02dd07ab96ab` `tests/test_live_public_strategy_source_audit_v2_8_b.py`
- `266f558bbb68d3d90b62e64d9a02e3633c091940cc5a9592ec48d561d08bca9d` `data/reports/v2_8_b_live_public_strategy_source_audit_latest.json`
- `ddca84335773401114d1c8a893268228efd713efc69d558c4343a2c58f822840` `data/reports/v2_8_b_live_public_strategy_source_audit_latest.md`
- `469b180ad23c58e7754d8296040aa13d93c175264fc72a306a00f8ad80d18853` `data/reports/V2_8_B_LIVE_PUBLIC_STRATEGY_SOURCE_AUDIT_PASS.marker`
- `91bd653c2eb564ff86930e5bd1461b5392b9d9892bcbd58f33d6392009087b52` `data/processed/v2_8_b_acceptance/v2_8_b_20260711_acceptance/live_public_strategy_source_audit.json`

## Source Status

Reachable:

- `catalog_msci_china_a_factor_2025`
- `catalog_panagora_china_a_factor`
- `catalog_hsi_smart_beta_index_series`
- `catalog_ken_french_factor_library`
- `catalog_msci_factor_indexes`
- `catalog_research_affiliates_vqm`
- `catalog_msci_low_volatility_construction`
- `catalog_aqr_low_vol_cycles`

Fetch errors:

- `catalog_spdji_a_share_factor`: HTTP 403
- `catalog_spdji_a_low_vol_high_dividend`: HTTP 403
- `catalog_spdji_hk_smart_beta`: HTTP 403
- `catalog_fama_french_five_factor`: HTTP 403

## Safety Boundary

- Live public URL audit only
- Metadata/hash only
- Raw text not stored
- Sample bytes not stored
- Fetch errors recorded
- No secret values
- No cookies
- No API keys
- Requires sandbox before suggestion
- No real trade
- No broker API
- No trading webhook
- No strategy auto-mutation
- No production record mutation

Next target: `V2.8-C Source Audit To Sandbox Refresh Queue`.

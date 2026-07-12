# V2.8-A Acceptance Report

## Result

- Target: `V2.8-A Public Strategy Source Audit`
- Status: `PASS`
- Run ID: `v2_8_a_20260711_acceptance`
- Acceptance command:
  - `.venv/bin/python scripts/validate_v2_8_a_public_strategy_source_audit.py --run-id v2_8_a_20260711_acceptance`
- Exit code: `0`
- Related regression:
  - `4 passed`
  - `32 passed`

## What Passed

`V2.8-A` adds a public strategy research source audit layer. It verifies that
catalogued A/H/US strategy sources can be audited with metadata/hash-only
evidence before they seed sandbox hypotheses or suggestion drafts.

Important current state:

- Audited sources: `12`
- Reachable sources in fixture audit: `12`
- Market coverage: A, H, US, GLOBAL
- Strategy source audit does not store raw text or sample bytes.
- Strategy source audit cannot create recommendations or orders.

This stage proves the audit shape and safety boundary. It uses fixture fetches
for stable acceptance; a live public-source reachability run is the next target.

## Evidence

- `data/reports/V2_8_A_PUBLIC_STRATEGY_SOURCE_AUDIT_PASS.marker`
- `data/reports/v2_8_a_public_strategy_source_audit_latest.json`
- `data/reports/v2_8_a_public_strategy_source_audit_latest.md`
- `data/processed/v2_8_a_acceptance/v2_8_a_20260711_acceptance/public_strategy_source_audit.json`

SHA256:

- `3517b9a86872063a106d0c6926aa68195323f3bae92c1daba18e90e5555307e9` `aegis/strategy/source_audit.py`
- `69bfc6fede320baba7ee2b6df921c5148c376523d27a0854c45626f959dc14e4` `scripts/validate_v2_8_a_public_strategy_source_audit.py`
- `528f6ac0e6552710d5371b1fb0624369b8491ae93c6f23638b0661be4cdd7774` `tests/test_public_strategy_source_audit_v2_8_a.py`
- `fd9ab63f199e93e37218c5b80d7840fb322b0afd1c3d9fd3ddd8ee4c660b6923` `data/reports/v2_8_a_public_strategy_source_audit_latest.json`
- `d491d6b6a551a68e27b6eb51f8897ea490e31b797d9e1882a325c79b780da695` `data/reports/v2_8_a_public_strategy_source_audit_latest.md`
- `2beb77dd96c35ae0730037c47c8bd73276b751fdba88d59b05e6c1e872480935` `data/reports/V2_8_A_PUBLIC_STRATEGY_SOURCE_AUDIT_PASS.marker`
- `ac16c583552bcd26f175a2905b4c55d8a0324764edb2184c0ccb3079b277634b` `data/processed/v2_8_a_acceptance/v2_8_a_20260711_acceptance/public_strategy_source_audit.json`

## Safety Boundary

- Metadata/hash only
- Raw text not stored
- Sample bytes not stored
- No secret values
- No cookies
- No API keys
- Requires sandbox before suggestion
- No real trade
- No broker API
- No trading webhook
- No strategy auto-mutation
- No production record mutation

Next target: `V2.8-B Live Public Strategy Source Audit`.

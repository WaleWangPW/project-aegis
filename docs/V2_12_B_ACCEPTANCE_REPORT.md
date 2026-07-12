# V2.12-B Acceptance Report

Acceptance target: `V2.12-B H-US Provider Metadata Activation`

Purpose: convert the verified V2.12-A EODHD/Twelve Data H/US provider
capabilities into a non-secret metadata and routing proposal. This stage does
not mutate production provider config, does not enable suggestion paths, and
does not fetch network data.

## Expected Evidence

- `data/reports/V2_12_B_H_US_PROVIDER_METADATA_ACTIVATION_PASS.marker`
- `data/reports/v2_12_b_h_us_provider_metadata_activation_latest.json`
- `data/reports/v2_12_b_h_us_provider_metadata_activation_latest.md`
- `data/processed/v2_12_b_acceptance/<run_id>/h_us_provider_metadata_activation.json`

## Acceptance Meaning

`V2.12-B PASS` means:

- EODHD is proposed as the primary Hong Kong daily-bar provider.
- EODHD is proposed as the primary U.S. daily-bar provider.
- Twelve Data is proposed as the U.S. fallback provider.
- Twelve Data Hong Kong remains blocked until plan and symbol route are proven.
- Only env var names, provider names, route IDs, capability summaries, and
  hashes are stored.

## Boundary

- Metadata/routing proposal only.
- No API key values.
- No request URL storage.
- No raw payload storage.
- No network fetch.
- No production provider config mutation.
- No candidate or suggestion path activation.
- No real trade.
- No broker API.
- No trading webhook.
- No order placement.
- Dashboard Contract unchanged.

## Next

`V2.12-C H-US Historical Cache Readiness Dry Run`: use the approved metadata
proposal to design a bounded historical-cache readiness dry run before any
candidate/suggestion path consumes H/US provider data.

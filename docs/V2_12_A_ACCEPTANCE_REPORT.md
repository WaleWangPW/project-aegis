# V2.12-A Acceptance Report

Acceptance target: `V2.12-A EODHD Twelve Data H-US Provider Probe`

Purpose: verify the user-provided EODHD and Twelve Data keys as bounded H/US
market-data provider inputs. This stage is a provider capability probe only. It
does not route production decisions, generate suggestions, or write trading
records.

## Expected Evidence

- `data/reports/V2_12_A_EODHD_TWELVE_H_US_PROVIDER_PROBE_PASS.marker`
- `data/reports/v2_12_a_eodhd_twelve_h_us_provider_probe_latest.json`
- `data/reports/v2_12_a_eodhd_twelve_h_us_provider_probe_latest.md`
- `data/processed/v2_12_a_acceptance/<run_id>/eodhd_twelve_h_us_provider_probe_report.json`

## Acceptance Meaning

`V2.12-A PASS` means at least one H-share provider and at least one U.S. provider
returned valid daily-bar summaries while storing no token values, no request
URLs, and no raw payloads.

The expected first result is:

- EODHD: U.S. daily bars pass.
- EODHD: Hong Kong daily bars pass with EODHD symbols such as `0700.HK`.
- Twelve Data: U.S. daily bars pass.
- Twelve Data: Hong Kong daily bars may remain failed/plan-limited until a
  later metadata activation stage proves the correct plan and symbol route.

## Boundary

- Provider capability probe only.
- Env var names only; no token values.
- No raw payload storage.
- No request URL storage.
- No real trade.
- No broker API.
- No trading webhook.
- No order placement.
- No production record mutation.
- Dashboard Contract unchanged.

## Next

`V2.12-B H-US Provider Metadata Activation`: convert the proven provider
capabilities into non-secret metadata and routing proposals before any
candidate/suggestion path uses them.

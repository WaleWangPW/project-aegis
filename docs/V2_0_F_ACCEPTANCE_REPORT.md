# Project Aegis V2.0-F Acceptance Report

Status: `V2.0-F PASS`

Accepted at: `2026-07-11T17:21:03.407108+08:00`

Acceptance target: `V2.0-F Official Source Fetcher`

## What V2.0-F Proves

`V2.0-F Official Source Fetcher` proves that Project Aegis can perform a
policy-gated live fetch from an approved official source.

The accepted path used the SEC public data API for Apple filings metadata:

- URL: `https://data.sec.gov/submissions/CIK0000320193.json`
- Source: `src_sec_company_filings`
- Evidence level: `verified_primary`
- Retention policy: `summary_only`
- Network used: `true`

The fetcher requires Source Policy Gate approval, a contact-style User-Agent,
and stores only metadata summary plus hash. It does not store raw bytes, use
cookies, store secrets, bypass paywalls, or access broker systems.

## Evidence

- Command: `.venv/bin/python scripts/validate_v2_0_f_official_source_fetcher.py --run-id v2_0_f_20260711_acceptance_live_sec --live-sec --user-agent ProjectAegis/0.1 weihongwang@example.com`
- Exit code: `0`
- Marker: `data/reports/V2_0_F_OFFICIAL_SOURCE_FETCHER_PASS.marker`
- Report JSON: `data/reports/v2_0_f_official_source_fetcher_latest.json`
- Report Markdown: `data/reports/v2_0_f_official_source_fetcher_latest.md`
- Isolated run dir: `data/processed/v2_0_f_acceptance/v2_0_f_20260711_acceptance_live_sec`
- Network used: `true`
- Dashboard Contract changed: `false`
- Production records written: `false`

## Acceptance Checks

- Official source fetched: `PASS`
- Summary created: `PASS`
- Hash created: `PASS`
- Raw bytes not stored: `PASS`
- Denied source blocked: `PASS`
- No cookie or secret headers: `PASS`
- No broker or real trade: `PASS`

Summary:

- Source id: `src_sec_company_filings`
- Symbol: `AAPL`
- Market: `US`
- Evidence level: `verified_primary`
- Retention policy: `summary_only`
- Summary: `JSON document with keys: addresses, category, cik, description, ein, entityType, exchanges, filings, fiscalYearEnd, flags, formerNames, insiderTransactionForIssuerExists.`

## Hashes

- Report JSON SHA256: `6ad1e1d8b04057de9a577917c7c4e7a9eac540de31faecd57e827e8a78de04c8`
- Report Markdown SHA256: `5b101f4fc4e876f4a67cf15edc41591861e1f56f212eb8e765327f429a5a7ff4`
- Marker SHA256: `0deb02270aedfaecff735be4559a9d17ee62c8480f1ac13fdafea407977dbc19`
- Item JSON SHA256: `d5388bfdda5b2ebdcd7b7def830eb46c73dd1edd07bcdad75628677d827d7f5f`

## Safety Boundary

- Policy Gate required.
- No cookie access.
- No secret storage.
- No paywall bypass.
- No raw article storage.
- No broker API.
- No real trade.
- No webhook.
- No strategy mutation.
- No Dashboard Contract change.
- No production `data/records` mutation.

## Next Version Target

After `V2.0-F PASS`, the next target is `V2.1-A Historical Strategy Sandbox`,
which should use existing historical records to simulate and verify strategy
candidate viability before any recommendation is promoted for user use.


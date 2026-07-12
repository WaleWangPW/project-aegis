# V2.8-H Acceptance Report — Concrete Candidate Usable Brief

## Result

PASS.

V2.8-H turns the V2.8-G concrete candidate bindings into a user-readable
concrete candidate brief. It shows A/H/US concrete candidates, blocked paths,
source labels, evidence links, and the manual external execution boundary.

The current source mode is `approved_fixture_not_live_market_data`. This is not
live API data, not live price advice, and not an order.

## Command

```bash
.venv/bin/python scripts/validate_v2_8_h_concrete_candidate_usable_brief.py --run-id v2_8_h_20260711_acceptance
```

Exit code: `0`

## Evidence

- Report JSON: `data/reports/v2_8_h_concrete_candidate_usable_brief_latest.json`
- Report Markdown: `data/reports/v2_8_h_concrete_candidate_usable_brief_latest.md`
- Pass marker: `data/reports/V2_8_H_CONCRETE_CANDIDATE_USABLE_BRIEF_PASS.marker`
- Brief JSON: `data/processed/v2_8_h_acceptance/v2_8_h_20260711_acceptance/concrete_candidate_usable_brief.json`
- Brief Markdown: `data/processed/v2_8_h_acceptance/v2_8_h_20260711_acceptance/concrete_candidate_usable_brief.md`
- Source bindings copy: `data/processed/v2_8_h_acceptance/v2_8_h_20260711_acceptance/source_concrete_candidate_bindings.json`

## Summary

- Brief items: `12`
- Concrete candidate items: `9`
- Blocked paths: `3`
- Candidate markets: `A`, `H`, `US`
- Source mode: `approved_fixture_not_live_market_data`

Concrete candidate items:

- A: `600519.SH`, `600036.SH`, `601398.SH`
- H: `00700.HK`, `00005.HK`, `00941.HK`
- US: `CRCL`, `MSFT`, `NVDA`

Blocked paths:

- `A_VALUE_QUALITY_PAPER_BASKET`
- `H_SMART_BETA_PAPER_BASKET`
- `US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET`

## Safety Checks

- Candidate count is at least 9.
- A/H/US concrete candidates are present.
- Blocked paths are visible.
- Fixture status is explicit and honest.
- Every item is simulation-only.
- Manual external execution only.
- No live order.
- No live price.
- No position size.
- No broker API.
- No webhook.
- No production records written.
- Dashboard Contract unchanged.

## Verification

```bash
.venv/bin/python -m pytest tests/test_concrete_candidate_usable_brief_v2_8_h.py -q
```

Exit code: `0`

Result: `2 passed in 0.07s`

```bash
.venv/bin/python -m pytest tests/test_concrete_candidate_usable_brief_v2_8_h.py tests/test_concrete_candidate_binding_refresh_v2_8_g.py tests/test_refresh_queue_usable_brief_v2_8_f.py tests/test_refresh_queue_suggestion_gate_v2_8_e.py tests/test_candidate_refresh_v2_5_b.py tests/test_usable_suggestion_brief_v2_6_a.py -q
```

Exit code: `0`

Result: `18 passed in 0.12s`

## SHA256

- `scripts/validate_v2_8_h_concrete_candidate_usable_brief.py`: `06cd12511930127fe01d264af32ca51ee39db5179a7bfdbc31d19bb7a421865d`
- `tests/test_concrete_candidate_usable_brief_v2_8_h.py`: `535ea2a2a0e091289185f181793336b85a25dd75a6d50f34fec457b55d31a375`
- `data/reports/v2_8_h_concrete_candidate_usable_brief_latest.json`: `47290925b2efd7d3a314ab3cf89d2fe9c8ef25cac0e261f3dd3ac9575de0452b`
- `data/reports/V2_8_H_CONCRETE_CANDIDATE_USABLE_BRIEF_PASS.marker`: `35033429060bc951f8cce3f5fca834eceeb23dfd83a6430ddb7cb6e5ab83d5e2`
- `data/processed/v2_8_h_acceptance/v2_8_h_20260711_acceptance/concrete_candidate_usable_brief.json`: `9cd55b38b5a5e4b2269999369253e857a354c8f391ec0bb4b0614029830480ee`

## Next Target

`V2.8-I Real User API Handoff Refresh`: prepare the exact non-secret connector
metadata checklist for replacing approved fixture candidates with user-provided
API-backed candidate refresh. Do not collect API keys in files or chat.

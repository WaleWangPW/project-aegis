# V2.8-I Acceptance Report — Real User API Handoff Refresh

## Result

PASS.

V2.8-I prepares the non-secret connector metadata path for replacing approved
fixture candidate sources with user-provided API-backed candidate refresh.

This stage does not connect to a real user API yet. It defines the handoff
document, local template, validator, and tests needed before a future live
candidate-refresh dry run.

## Command

```bash
.venv/bin/python scripts/validate_v2_8_i_real_user_api_handoff_refresh.py --run-id v2_8_i_20260711_acceptance
```

Exit code: `0`

## Evidence

- Report JSON: `data/reports/v2_8_i_real_user_api_handoff_refresh_latest.json`
- Report Markdown: `data/reports/v2_8_i_real_user_api_handoff_refresh_latest.md`
- Pass marker: `data/reports/V2_8_I_REAL_USER_API_HANDOFF_REFRESH_PASS.marker`
- Run directory: `data/processed/v2_8_i_acceptance/v2_8_i_20260711_acceptance/`
- Refresh handoff: `docs/V2_8_I_REAL_USER_API_HANDOFF_REFRESH.md`
- User template: `config/external_api_connectors.user-template.json`

## Summary

- Connector templates: `1`
- Allowed connectors: `1`
- Required env var names: `AEGIS_CANDIDATE_REFRESH_API_KEY`
- Real user config status: `blocked_missing_metadata`
- Next target: `V2.8-J Real User API Candidate Refresh Dry Run After Local Metadata`

Required candidate refresh fields:

- `items_path`
- `symbol_field`
- `market_field`
- `name_field`
- `score_field`
- `status_field`
- `allowed_markets`
- `max_items_per_market`
- `freshness_policy`
- `candidate_summary_only`

## Safety Checks

- Non-secret metadata template only.
- Env var values are not stored.
- Env var names only.
- No raw API response.
- No request headers stored.
- Candidate refresh is research input only.
- Historical sandbox still required.
- Suggestion Gate still required.
- Simulation-only.
- Manual external execution only.
- No real trade.
- No broker API.
- No trading webhook.
- No order placement.
- No production records written.
- Dashboard Contract unchanged.

## Verification

```bash
.venv/bin/python -m pytest tests/test_real_user_api_handoff_refresh_v2_8_i.py -q
```

Exit code: `0`

Result: `7 passed in 0.08s`

```bash
.venv/bin/python -m pytest tests/test_real_user_api_handoff_refresh_v2_8_i.py tests/test_user_api_candidate_refresh_v2_5_c.py tests/test_live_api_metadata_activation_v2_7_a.py tests/test_live_api_dry_run_v2_7_b.py tests/test_concrete_candidate_usable_brief_v2_8_h.py -q
```

Exit code: `0`

Result: `22 passed in 0.13s`

## SHA256

- `scripts/validate_v2_8_i_real_user_api_handoff_refresh.py`: `a2918b9465bb8013412042781eeb74c970be252023a6900c525c71d9500edca4`
- `tests/test_real_user_api_handoff_refresh_v2_8_i.py`: `61dd869d3908de42c97d37f4d485b52b1a6b469b1a6f3202a0de091a33b6df39`
- `docs/V2_8_I_REAL_USER_API_HANDOFF_REFRESH.md`: `cff20dfc07d18f0fada2be639674dc2ccc6e34827a70a1f8ec67cf333732cfa3`
- `config/external_api_connectors.user-template.json`: `930bc3f7c2d63bc7e4b817d31b1d20c772292d41fee0be8cc0ed012e2294a01f`
- `docs/API_CONFIGURATION_HANDOFF.md`: `3a1b94906f702e3f865325cb930abfdb0deabfca859fa19861c6172a0316cd50`
- `data/reports/v2_8_i_real_user_api_handoff_refresh_latest.json`: `dd47b2049aec161b7995453b12b9ef11d6a1cc77e0fcacaf8e0a3ff7b9d2cbe1`
- `data/reports/V2_8_I_REAL_USER_API_HANDOFF_REFRESH_PASS.marker`: `92a48cf8e461411c46656cfe3f97f2eeb9f613d3945c9a7860945e65c2cdb815`

## Next Target

`V2.8-J Real User API Candidate Refresh Dry Run After Local Metadata`: run the
bounded candidate-refresh dry run only after the user provides non-secret local
metadata and configures the required local env var. Do not collect API key
values in files or chat.

# V2.8-J Acceptance Report — Real User API Candidate Refresh Dry Run

## Result

PASS.

V2.8-J adds the bounded candidate-refresh dry-run scaffold for the user API
path. It proves the fixture-ready path can parse API candidate summaries in
memory, store summary/hash/status evidence, build an API candidate registry,
and bind A/H/US candidate refresh output back into the existing simulation-only
Suggestion Gate chain.

The real user API path remains `blocked_missing_metadata` until the user
provides local non-secret metadata and the required local env var.

## Command

```bash
.venv/bin/python scripts/validate_v2_8_j_real_user_api_candidate_refresh_dry_run.py --run-id v2_8_j_20260711_acceptance
```

Exit code: `0`

## Evidence

- Report JSON: `data/reports/v2_8_j_real_user_api_candidate_refresh_dry_run_latest.json`
- Report Markdown: `data/reports/v2_8_j_real_user_api_candidate_refresh_dry_run_latest.md`
- Pass marker: `data/reports/V2_8_J_REAL_USER_API_CANDIDATE_REFRESH_DRY_RUN_PASS.marker`
- Run directory: `data/processed/v2_8_j_acceptance/v2_8_j_20260711_acceptance/`

## Summary

- Fixture dry-run status: `completed`
- Fixture bound markets: `A`, `H`, `US`
- Fixture bound count: `3`
- Fixture blocked count: `3`
- Real user dry-run status: `blocked_missing_metadata`
- Real user blocked by: `missing_connector_metadata`
- Next target: `V2.8-K API-Backed Candidate Usable Brief After Real Metadata`

## Safety Checks

- Activation gate runs before fetch.
- Missing real-user metadata does not fetch.
- Raw API payload is parsed in memory only.
- Raw bytes are not stored.
- Request headers are not stored.
- Env var values are not stored.
- Env var names only.
- Query values are not stored.
- Summary/hash/status/candidate summaries only.
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
.venv/bin/python -m pytest tests/test_real_user_api_candidate_refresh_dry_run_v2_8_j.py -q
```

Exit code: `0`

Result: `4 passed in 0.09s`

```bash
.venv/bin/python -m pytest tests/test_real_user_api_candidate_refresh_dry_run_v2_8_j.py tests/test_real_user_api_handoff_refresh_v2_8_i.py tests/test_user_api_candidate_refresh_v2_5_c.py tests/test_live_api_dry_run_v2_7_b.py tests/test_concrete_candidate_usable_brief_v2_8_h.py -q
```

Exit code: `0`

Result: `22 passed in 0.12s`

## SHA256

- `aegis/strategy/candidate_refresh.py`: `f76fe014dab2b9fb392aa0197a536a51b25f069b26b3c0dce9dfe907fe292e2e`
- `scripts/validate_v2_8_j_real_user_api_candidate_refresh_dry_run.py`: `be747117d7d79524f2e0d1eddb58ea9603ae17434a395fc675f30dedb6ca1529`
- `tests/test_real_user_api_candidate_refresh_dry_run_v2_8_j.py`: `6c76b21459317dc81766a3667450e0fbc8ce639b0f6565455f1f0b3f70e7e737`
- `data/reports/v2_8_j_real_user_api_candidate_refresh_dry_run_latest.json`: `8f25f83aaac7861ec3004cde92dfeea0dfd5865be70f39c68e6be55b502250e1`
- `data/reports/V2_8_J_REAL_USER_API_CANDIDATE_REFRESH_DRY_RUN_PASS.marker`: `5d67679c536bf3b0fc88fdb5666bc76f1f673d075c4b8a9d5b009aa0ad3abf77`

## Next Target

`V2.8-K API-Backed Candidate Usable Brief After Real Metadata`: after real
metadata/env var are available and the real user API dry-run completes, convert
API-backed candidate refresh evidence into a user-readable simulation-only
brief. Until then, do not claim live API candidates are available.

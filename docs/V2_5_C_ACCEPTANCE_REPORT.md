# V2.5-C Acceptance Report

## Result

- Target: `V2.5-C User API Live Candidate Refresh`
- Status: `PASS`
- Run ID: `v2_5_c_20260711_acceptance_rerun`
- Acceptance command:
  - `.venv/bin/python scripts/validate_v2_5_c_user_api_candidate_refresh.py --run-id v2_5_c_20260711_acceptance_rerun`
- Exit code: `0`
- Related regression:
  - `50 passed`

## What Passed

`V2.5-C` added a bounded user API candidate-refresh entrypoint. The acceptance run used fixture API mode to prove the live API shape, env-var auth handling, candidate summary parsing, and A/H/US candidate binding.

Important boundary: this is still fixture mode. No real user API metadata/env var has been provided yet, so the real user config remains `blocked_missing_metadata`.

Summary:

- Fixture API dry-run: `PASS`
- Fixture mode: `true`
- Network used: `false`
- Real user config status: `blocked_missing_metadata`
- Raw bytes stored: `false`
- Request headers stored: `false`
- Secret value serialized: `false`
- Bound markets from API candidate summaries: `A`, `H`, `US`

API fixture candidate bindings:

- A-share low-volatility dividend draft:
  - `600036.SH` 招商银行
- Hong Kong low-volatility dividend draft:
  - `00700.HK` Tencent Holdings
- U.S. value-quality-momentum draft:
  - `MSFT` Microsoft

Still blocked:

- A-share value-quality multi-factor: `strategy_sandbox_not_passed`
- Hong Kong smart-beta multi-factor: `strategy_sandbox_not_passed`
- U.S. low-volatility risk overlay: `strategy_sandbox_not_passed`

## Evidence

- `data/reports/V2_5_C_USER_API_CANDIDATE_REFRESH_PASS.marker`
- `data/reports/v2_5_c_user_api_candidate_refresh_latest.json`
- `data/reports/v2_5_c_user_api_candidate_refresh_latest.md`
- `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/api_candidate_source_registry.json`
- `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/api_refreshed_candidate_bindings.json`
- `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/fixture_candidate_api_dry_run/api_research_dry_run_report.json`
- `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/fixture_candidate_api_dry_run/api_fetch_item.json`

SHA256:

- `668d2b928552c8eccfd98a28aa2abfc565370b4909bfcb53406990d0308f245d` `aegis/models/candidate_source.py`
- `b278b073a742bf857db4f0e52fc4206620d5fb288359d599e1a10e5f0a4c22a2` `aegis/strategy/candidate_refresh.py`
- `ee9c8c9a0513deb7db75ed6239c89d7fedace4c68000897727855f6d77459706` `scripts/validate_v2_5_c_user_api_candidate_refresh.py`
- `4f0319b487dc221fa2a357b994751ed869ac1c784fe80ff48de24e45f9858dd6` `tests/test_user_api_candidate_refresh_v2_5_c.py`
- `4ce3f176be384955d82d50d31d353281eb8000c710033d5363a6da1bbc1bf92a` `data/reports/v2_5_c_user_api_candidate_refresh_latest.json`
- `c22b1978920bd6dbdfafa7cf2218a4d6e3f8794daca23055ce488cb3c82719bc` `data/reports/v2_5_c_user_api_candidate_refresh_latest.md`
- `d61ec86e02fdf0530348c0421e4ce9a094a0115cc5ccd075a6381f2dcfa260c1` `data/reports/V2_5_C_USER_API_CANDIDATE_REFRESH_PASS.marker`
- `9f277b43d868a1e41fbb4cf154054d8c3a59813c5d78b1535409e52c1ffa1ed1` `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/api_candidate_source_registry.json`
- `90f2045a8f5fb7a4828075794fda6ab4246ee9c8415cb455c1dacf8e9c054ac6` `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/api_refreshed_candidate_bindings.json`
- `8b954a40884886ef8313e5c19222aadf8ea2d6eea3ab6901ab4f9a96495e3d8c` `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/fixture_candidate_api_dry_run/api_research_dry_run_report.json`
- `dbe9f4a08ab87345c4022a7c58948c9d1844ff09500d9fbe94a0841cd0099b3b` `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/fixture_candidate_api_dry_run/api_fetch_item.json`

## Safety Boundary

- Fixture mode, not real user API yet
- Real user config remains `blocked_missing_metadata`
- Env var names only
- API key value not stored
- Raw bytes not stored
- Request headers not stored
- Candidate summaries only
- No real trade
- No broker API
- No trading webhook
- No production record mutation
- Dashboard Contract unchanged
- User must decide and execute manually outside Aegis

Next work can either wait for user-provided API metadata/env var to run real live refresh, or proceed to `V2.6-A Usable Suggestion Brief` using the current evidence-labeled fixture/API-dry-run candidates.


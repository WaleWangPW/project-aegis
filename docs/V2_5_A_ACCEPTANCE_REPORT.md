# V2.5-A Acceptance Report

## Result

- Target: `V2.5-A Approved Candidate Binding For Suggestion Drafts`
- Status: `PASS`
- Run ID: `v2_5_a_20260711_acceptance`
- Acceptance command:
  - `.venv/bin/python scripts/validate_v2_5_a_candidate_binding.py --run-id v2_5_a_20260711_acceptance`
- Exit code: `0`
- Related regression:
  - `114 passed`

## What Passed

`V2.5-A` bound `V2.4-D` simulation-only suggestion drafts to concrete approved candidate sources where evidence exists.

Summary:

- Suggestion drafts checked: `6`
- Candidate bindings: `6`
- Bound bindings: `2`
- Blocked bindings: `4`
- Bound markets: `A`, `US`
- Blocked markets: `A`, `H`, `US`

Bound candidates:

- `sug_research_hyp_a_low_vol_dividend_defensive`
  - Source: `data/reports/a_share_watchlist_latest.json`
  - Candidates: `600519.SH`, `600036.SH`, `000858.SZ`, `000001.SZ`, `601398.SH`
- `sug_research_hyp_us_value_quality_momentum`
  - Source: `data/desktop/aegis_status.json`
  - Candidate: `CRCL`

Blocked bindings:

- `sug_research_hyp_a_value_quality_multifactor`
  - Reason: `strategy_sandbox_not_passed`
- `sug_research_hyp_h_low_vol_dividend`
  - Reason: `missing_candidate_source`
- `sug_research_hyp_h_smart_beta_multifactor`
  - Reason: `strategy_sandbox_not_passed`
- `sug_research_hyp_us_low_vol_risk_overlay`
  - Reason: `strategy_sandbox_not_passed`

The Hong Kong low-volatility dividend draft passed the strategy sandbox, but it is blocked at candidate binding because no approved concrete H-share candidate source exists yet. This is an honest data-source gap, not a strategy failure.

## Evidence

- `data/reports/V2_5_A_APPROVED_CANDIDATE_BINDING_PASS.marker`
- `data/reports/v2_5_a_candidate_binding_latest.json`
- `data/reports/v2_5_a_candidate_binding_latest.md`
- `data/processed/v2_5_a_acceptance/v2_5_a_20260711_acceptance/candidate_bindings.json`
- `data/processed/v2_5_a_acceptance/v2_5_a_20260711_acceptance/source_suggestion_drafts.json`

SHA256:

- `1fc54160226c5d8d24f2d5434c798d895bb11f36c04d7ea4bc2a15b778c4af3e` `aegis/models/candidate_binding.py`
- `dcb1af77664356204d37c46db316e17e043a8419e4ae725e33d00c3f706e0ee8` `aegis/strategy/candidate_binding.py`
- `b66cf2fa92ce269e3dfd4de21edf79595d2c4a356963bf838b7683dbcd2ee21a` `scripts/validate_v2_5_a_candidate_binding.py`
- `06dc1206932db17b7415c4784f8be8a06c108737b90b81b162f49d0b897c4dc8` `tests/test_candidate_binding_v2_5_a.py`
- `a0ac6e1c6b7388e6f88ae14b63ade90310ea303fc40c1a34e116899cd0aa9fbb` `data/reports/v2_5_a_candidate_binding_latest.json`
- `a2324c6a010549448ce607f2ed6a24404f69a596ab0881aab43528c295cfcda4` `data/reports/v2_5_a_candidate_binding_latest.md`
- `89542f61332f814fbfddf80b64d569caef5a74dd3994f3d68ccf5221f2fc32bf` `data/reports/V2_5_A_APPROVED_CANDIDATE_BINDING_PASS.marker`
- `45c389390dd98fec9f8d8b4b723c215262f35e13c14b0e439f4be496f92ff069` `data/processed/v2_5_a_acceptance/v2_5_a_20260711_acceptance/candidate_bindings.json`
- `35a925fbb4c3a6a4e91ab94d2e3150dbe312dcc7a0161ea9775b439293770f92` `data/processed/v2_5_a_acceptance/v2_5_a_20260711_acceptance/source_suggestion_drafts.json`

## Safety Boundary

These are candidate bindings for simulation-only drafts.

- Not a production `RecommendationRecord`
- Not an order
- No real trade
- No broker API
- No trading webhook
- No secret storage
- No production record mutation
- Dashboard Contract unchanged
- User must decide and execute manually outside Aegis

Next work should add an approved H-share candidate source and/or live candidate refresh before claiming full A/H/US concrete suggestion coverage.


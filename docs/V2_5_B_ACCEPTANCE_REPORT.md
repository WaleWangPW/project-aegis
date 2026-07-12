# V2.5-B Acceptance Report

## Result

- Target: `V2.5-B Approved Live Candidate Refresh`
- Status: `PASS`
- Run ID: `v2_5_b_20260711_acceptance`
- Acceptance command:
  - `.venv/bin/python scripts/validate_v2_5_b_candidate_refresh.py --run-id v2_5_b_20260711_acceptance`
- Exit code: `0`
- Related regression:
  - `119 passed`

## What Passed

`V2.5-B` added an approved refreshable candidate-source layer and refreshed candidate bindings for A/H/US strategy suggestion drafts.

Important boundary: this run uses approved fixture candidate sources. It proves the refresh and binding interface, including H-share coverage, but it is not live market data yet. Live user API refresh remains `blocked_missing_metadata` until non-secret connector metadata and local env vars are provided.

Summary:

- Candidate sources: `3`
- Suggestion drafts checked: `6`
- Candidate bindings: `6`
- Bound bindings: `3`
- Blocked bindings: `3`
- Bound markets: `A`, `H`, `US`
- Candidate counts by market:
  - `A`: `3`
  - `H`: `3`
  - `US`: `3`
- User API live status: `blocked_missing_metadata`

Bound refreshed candidates:

- A-share low-volatility dividend draft:
  - `600519.SH` 贵州茅台
  - `600036.SH` 招商银行
  - `601398.SH` 工商银行
- Hong Kong low-volatility dividend draft:
  - `00700.HK` Tencent Holdings
  - `00005.HK` HSBC Holdings
  - `00941.HK` China Mobile
- U.S. value-quality-momentum draft:
  - `CRCL` Circle Internet Group
  - `MSFT` Microsoft
  - `NVDA` NVIDIA

Still blocked:

- A-share value-quality multi-factor: `strategy_sandbox_not_passed`
- Hong Kong smart-beta multi-factor: `strategy_sandbox_not_passed`
- U.S. low-volatility risk overlay: `strategy_sandbox_not_passed`

## Evidence

- `data/reports/V2_5_B_APPROVED_CANDIDATE_REFRESH_PASS.marker`
- `data/reports/v2_5_b_candidate_refresh_latest.json`
- `data/reports/v2_5_b_candidate_refresh_latest.md`
- `data/processed/v2_5_b_acceptance/v2_5_b_20260711_acceptance/approved_candidate_source_registry.json`
- `data/processed/v2_5_b_acceptance/v2_5_b_20260711_acceptance/refreshed_candidate_bindings.json`
- `data/processed/v2_5_b_acceptance/v2_5_b_20260711_acceptance/source_suggestion_drafts.json`

SHA256:

- `e5de4b6004d6a14fcd5b6691ac59c58fa44ba1593c4d19dfdf751fefc3e0d7f4` `aegis/models/candidate_source.py`
- `ff2093f653540fa66961d9140afccbfca41245c2b6b20924c24051a18c0199df` `aegis/strategy/candidate_refresh.py`
- `15f6038a70609975a39f6ba8d336da7da5a7467d0ab1ea1122a861def621829f` `scripts/validate_v2_5_b_candidate_refresh.py`
- `4dc3582a70851d084dfbbb803f0bb7e8ade179ad815c232b29bef617aa2c8f1a` `tests/test_candidate_refresh_v2_5_b.py`
- `682e51bdd83440fbd8eb631ebf43e507ca01a87405059ce1fee4e8cd14b0801e` `data/reports/v2_5_b_candidate_refresh_latest.json`
- `dabc8b2068b08df5a4a98ee60cd8e9b3886840965f6c5f95532a1bb627ee09d0` `data/reports/v2_5_b_candidate_refresh_latest.md`
- `b4733fa9b98f114688bcbd9a7003fdd5c5033e6738b1821ca898577bd84f2b34` `data/reports/V2_5_B_APPROVED_CANDIDATE_REFRESH_PASS.marker`
- `4c7967f6d391c335688a878864bb5af7a8a2d14f294c6c497f553c38df1c0957` `data/processed/v2_5_b_acceptance/v2_5_b_20260711_acceptance/approved_candidate_source_registry.json`
- `4e98aa53bae3c8186b85e35c971bb9973ce258de8a5d0923438323288abb86b9` `data/processed/v2_5_b_acceptance/v2_5_b_20260711_acceptance/refreshed_candidate_bindings.json`
- `35a925fbb4c3a6a4e91ab94d2e3150dbe312dcc7a0161ea9775b439293770f92` `data/processed/v2_5_b_acceptance/v2_5_b_20260711_acceptance/source_suggestion_drafts.json`

## Safety Boundary

- Approved sources only
- Fixture is not live market data
- User API live refresh requires non-secret metadata and local env vars
- No secret values stored
- No real trade
- No broker API
- No trading webhook
- No production record mutation
- Dashboard Contract unchanged
- User must decide and execute manually outside Aegis

Next work should be `V2.5-C User API Live Candidate Refresh`: use the existing external API connector metadata flow to refresh candidates from a user-provided API without storing secrets.


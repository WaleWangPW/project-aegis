# V2.8-G Acceptance Report — Concrete Candidate Binding Refresh

## Result

PASS.

V2.8-G binds the V2.8-E refresh-queue suggestion drafts to approved concrete
A/H/US candidate sources. This creates simulation-only concrete candidate
bindings, while preserving failed strategy paths as blocked.

This stage still does not use live market data. The current binding source is
an approved fixture registry. Real user API live binding remains blocked until
non-secret connector metadata and local env vars are provided.

## Command

```bash
.venv/bin/python scripts/validate_v2_8_g_concrete_candidate_binding_refresh.py --run-id v2_8_g_20260711_acceptance
```

Exit code: `0`

## Evidence

- Report JSON: `data/reports/v2_8_g_concrete_candidate_binding_refresh_latest.json`
- Report Markdown: `data/reports/v2_8_g_concrete_candidate_binding_refresh_latest.md`
- Pass marker: `data/reports/V2_8_G_CONCRETE_CANDIDATE_BINDING_REFRESH_PASS.marker`
- Concrete bindings: `data/processed/v2_8_g_acceptance/v2_8_g_20260711_acceptance/concrete_candidate_bindings.json`
- Approved source registry: `data/processed/v2_8_g_acceptance/v2_8_g_20260711_acceptance/approved_concrete_candidate_source_registry.json`
- Source drafts copy: `data/processed/v2_8_g_acceptance/v2_8_g_20260711_acceptance/source_refresh_queue_suggestion_drafts.json`

## Summary

- Source count: `3`
- Suggestion drafts: `6`
- Bindings: `6`
- Bound bindings: `3`
- Blocked bindings: `3`
- Bound markets: `A`, `H`, `US`
- Blocked markets: `A`, `H`, `US`
- Candidate counts by market: `A=3`, `H=3`, `US=3`
- Real user API live status: `blocked_missing_metadata`

Bound candidates:

- A: `600519.SH`, `600036.SH`, `601398.SH`
- H: `00700.HK`, `00005.HK`, `00941.HK`
- US: `CRCL`, `MSFT`, `NVDA`

Blocked paths:

- `sug_research_hyp_a_value_quality_multifactor`: `strategy_sandbox_not_passed`
- `sug_research_hyp_h_smart_beta_multifactor`: `strategy_sandbox_not_passed`
- `sug_research_hyp_us_low_vol_risk_overlay`: `strategy_sandbox_not_passed`

## Safety Checks

- A/H/US bound to concrete candidates.
- Blocked paths preserved.
- Every bound item has concrete candidate symbols.
- Fixture status is explicit and honest.
- Real user API remains blocked until metadata/env var setup.
- Approved sources only.
- Manual external execution only.
- No secret values stored.
- No real trade.
- No broker API.
- No webhook.
- No production record mutation.
- Dashboard Contract unchanged.

## Verification

```bash
.venv/bin/python -m pytest tests/test_concrete_candidate_binding_refresh_v2_8_g.py -q
```

Exit code: `0`

Result: `2 passed in 0.10s`

```bash
.venv/bin/python -m pytest tests/test_concrete_candidate_binding_refresh_v2_8_g.py tests/test_refresh_queue_usable_brief_v2_8_f.py tests/test_refresh_queue_suggestion_gate_v2_8_e.py tests/test_refresh_queue_historical_sandbox_v2_8_d.py tests/test_source_audit_sandbox_refresh_queue_v2_8_c.py tests/test_candidate_refresh_v2_5_b.py tests/test_user_api_candidate_refresh_v2_5_c.py tests/test_candidate_binding_v2_5_a.py -q
```

Exit code: `0`

Result: `30 passed in 0.14s`

## SHA256

- `scripts/validate_v2_8_g_concrete_candidate_binding_refresh.py`: `8d286966d0945f4a8d756cf9b72932d1cea0cc0929a3511232eb9facc1dd4eb9`
- `tests/test_concrete_candidate_binding_refresh_v2_8_g.py`: `c5de7305a4362d710844dda47a08c10e9f44d48f55b507ac0bca87fb3c7ab9a9`
- `data/reports/v2_8_g_concrete_candidate_binding_refresh_latest.json`: `fb6f1e79f8ace5a50527f1afee0eff6762badcca068acca371016d8d26035fe9`
- `data/reports/V2_8_G_CONCRETE_CANDIDATE_BINDING_REFRESH_PASS.marker`: `bd2fc5df717669ee551b57fe4761fa22397a8f92b4ef0db143785c7e31432b20`
- `data/processed/v2_8_g_acceptance/v2_8_g_20260711_acceptance/concrete_candidate_bindings.json`: `9f67a1afc266a40749077dfffb29fab7d842efdac53fb9e4df2d69c75f7ac789`

## Next Target

`V2.8-H Concrete Candidate Usable Brief`: turn V2.8-G concrete candidate
bindings into a user-readable concrete candidate brief, still simulation-only
and still not real trading.

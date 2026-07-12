# V2.8-D Acceptance Report — Refresh Queue Historical Sandbox Rerun

## Result

PASS.

V2.8-D consumes the accepted V2.8-C source-audit sandbox refresh queue and reruns
historical sandbox evaluation. It trims hypothesis evidence references to
reachable hashed sources before sandbox evaluation and excludes sources that
were blocked or failed in the live public audit.

This stage still does not create user-facing suggestions. Suggestion Gate is
required before any brief or recommendation draft can be updated.

## Command

```bash
.venv/bin/python scripts/validate_v2_8_d_refresh_queue_historical_sandbox.py --run-id v2_8_d_20260711_acceptance
```

Exit code: `0`

## Evidence

- Report JSON: `data/reports/v2_8_d_refresh_queue_historical_sandbox_latest.json`
- Report Markdown: `data/reports/v2_8_d_refresh_queue_historical_sandbox_latest.md`
- Pass marker: `data/reports/V2_8_D_REFRESH_QUEUE_HISTORICAL_SANDBOX_PASS.marker`
- Refreshed hypotheses: `data/processed/v2_8_d_acceptance/v2_8_d_20260711_acceptance/refreshed_hypotheses.json`
- Strategy candidates: `data/processed/v2_8_d_acceptance/v2_8_d_20260711_acceptance/refresh_queue_strategy_candidates.json`
- Historical cases: `data/processed/v2_8_d_acceptance/v2_8_d_20260711_acceptance/refresh_queue_historical_cases.jsonl`
- Sandbox report: `data/processed/v2_8_d_acceptance/v2_8_d_20260711_acceptance/refresh_queue_sandbox_report.json`

## Summary

- Refresh proposals evaluated: `3`
- Hypotheses evaluated: `6`
- Historical cases: `24`
- Passing hypotheses: `3`
- Failing hypotheses: `3`

Passing hypotheses:

- `hyp_a_low_vol_dividend_defensive`
- `hyp_h_low_vol_dividend`
- `hyp_us_value_quality_momentum`

Failing hypotheses:

- `hyp_a_value_quality_multifactor`
- `hyp_h_smart_beta_multifactor`
- `hyp_us_low_vol_risk_overlay`

Proposal mapping:

- `refresh_a_strategy_hypotheses_from_live_source_audit`: `hyp_a_low_vol_dividend_defensive`, `hyp_a_value_quality_multifactor`
- `refresh_h_strategy_hypotheses_from_live_source_audit`: `hyp_h_low_vol_dividend`, `hyp_h_smart_beta_multifactor`
- `refresh_us_strategy_hypotheses_from_live_source_audit`: `hyp_us_low_vol_risk_overlay`, `hyp_us_value_quality_momentum`

## Source Evidence Boundary

Reachable source refs used:

- `catalog_aqr_low_vol_cycles`
- `catalog_hsi_smart_beta_index_series`
- `catalog_ken_french_factor_library`
- `catalog_msci_china_a_factor_2025`
- `catalog_msci_factor_indexes`
- `catalog_msci_low_volatility_construction`
- `catalog_panagora_china_a_factor`
- `catalog_research_affiliates_vqm`

Blocked source refs excluded:

- `catalog_fama_french_five_factor`
- `catalog_spdji_a_low_vol_high_dividend`
- `catalog_spdji_a_share_factor`
- `catalog_spdji_hk_smart_beta`

## Safety Checks

- Uses V2.8-C refresh queue; no network fetch.
- Blocked source refs are excluded before sandbox evaluation.
- Historical sandbox evidence contains pass/fail metrics.
- Suggestion Gate is still required.
- No direct user-facing suggestion.
- No real trade.
- No broker API.
- No trading webhook.
- No strategy auto-mutation.
- No production record mutation.
- Dashboard Contract unchanged.

## Verification

```bash
.venv/bin/python -m pytest tests/test_refresh_queue_historical_sandbox_v2_8_d.py -q
```

Exit code: `0`

Result: `4 passed in 0.06s`

```bash
.venv/bin/python -m pytest tests/test_refresh_queue_historical_sandbox_v2_8_d.py tests/test_source_audit_sandbox_refresh_queue_v2_8_c.py tests/test_live_public_strategy_source_audit_v2_8_b.py tests/test_public_strategy_source_audit_v2_8_a.py tests/test_strategy_research_hypothesis_queue_v2_4_b.py tests/test_historical_sandbox_research_hypotheses_v2_4_c.py tests/test_research_hypotheses_suggestion_gate_v2_4_d.py -q
```

Exit code: `0`

Result: `32 passed in 0.14s`

## SHA256

- `aegis/strategy/source_audit_refresh_sandbox.py`: `c4a81b4e59ad309cb86a12404ab238ee1bdd32ec690797f99fe0bfc557fd638b`
- `scripts/validate_v2_8_d_refresh_queue_historical_sandbox.py`: `afe7a24e5b597da5cff55627e1f4991b05d64508bb45e62c9e29f5944b689d6c`
- `tests/test_refresh_queue_historical_sandbox_v2_8_d.py`: `782b62933ced472166d6471a067f07e47dd969141b0e7556e36662d5b25a9474`
- `data/reports/v2_8_d_refresh_queue_historical_sandbox_latest.json`: `8715eb44212f55091ec3970b5692862afbbe6283f4e81b26b585ff94944ff03e`
- `data/reports/V2_8_D_REFRESH_QUEUE_HISTORICAL_SANDBOX_PASS.marker`: `c7a00ae0c67b46f070e53a839a7cec8825126a396d75c08c8449beed816ce2ba`
- `data/processed/v2_8_d_acceptance/v2_8_d_20260711_acceptance/refresh_queue_sandbox_report.json`: `e5c69672d781abc8c9e982d7e6d4d1e43a7946bc07469121794fc8f357a82d4a`

## Next Target

`V2.8-E Refresh Queue Suggestion Gate Drafts`: route V2.8-D sandbox results
through Suggestion Gate. Passing hypotheses may become simulation-only draft
items; failing hypotheses and risk-vetoed paths must remain blocked.

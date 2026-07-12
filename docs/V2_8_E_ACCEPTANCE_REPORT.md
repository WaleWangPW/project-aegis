# V2.8-E Acceptance Report — Refresh Queue Suggestion Gate Drafts

## Result

PASS.

V2.8-E routes the accepted V2.8-D refresh-queue historical sandbox results
through the existing Suggestion Gate. Passing hypotheses become
simulation-only paper candidate drafts. Failing hypotheses remain blocked.

This stage still does not create real orders, broker actions, webhooks, live
prices, or position sizes. The user must decide and execute manually outside
Aegis.

## Command

```bash
.venv/bin/python scripts/validate_v2_8_e_refresh_queue_suggestion_gate.py --run-id v2_8_e_20260711_acceptance
```

Exit code: `0`

## Evidence

- Report JSON: `data/reports/v2_8_e_refresh_queue_suggestion_gate_latest.json`
- Report Markdown: `data/reports/v2_8_e_refresh_queue_suggestion_gate_latest.md`
- Pass marker: `data/reports/V2_8_E_REFRESH_QUEUE_SUGGESTION_GATE_PASS.marker`
- Suggestion drafts: `data/processed/v2_8_e_acceptance/v2_8_e_20260711_acceptance/refresh_queue_suggestion_drafts.json`
- Suggestion opportunities: `data/processed/v2_8_e_acceptance/v2_8_e_20260711_acceptance/refresh_queue_suggestion_opportunities.json`
- Source sandbox copy: `data/processed/v2_8_e_acceptance/v2_8_e_20260711_acceptance/source_refresh_queue_sandbox_report.json`

## Summary

- Opportunities: `6`
- Suggestion drafts: `6`
- Allowed simulation-only drafts: `3`
- Blocked drafts: `3`

Allowed drafts:

- `sug_research_hyp_a_low_vol_dividend_defensive`
- `sug_research_hyp_h_low_vol_dividend`
- `sug_research_hyp_us_value_quality_momentum`

Blocked drafts:

- `sug_research_hyp_a_value_quality_multifactor`
- `sug_research_hyp_h_smart_beta_multifactor`
- `sug_research_hyp_us_low_vol_risk_overlay`

## Draft Boundary

Allowed drafts use paper basket symbols only:

- `A_LOW_VOL_DIVIDEND_PAPER_BASKET`
- `H_LOW_VOL_DIVIDEND_PAPER_BASKET`
- `US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET`

They are not live-price recommendations, not position-size recommendations,
and not broker orders.

## Safety Checks

- Source is V2.8-D sandbox evidence.
- Allowed count matches sandbox PASS count.
- Blocked count matches sandbox FAIL count.
- Failed sandbox hypotheses are blocked by `strategy_sandbox_not_passed`.
- All drafts are simulation-only.
- User must execute manually outside Aegis.
- No live price or position size.
- No real trade.
- No broker API.
- No trading webhook.
- No secret storage.
- No production record mutation.
- Dashboard Contract unchanged.

## Verification

```bash
.venv/bin/python -m pytest tests/test_refresh_queue_suggestion_gate_v2_8_e.py -q
```

Exit code: `0`

Result: `3 passed in 0.07s`

```bash
.venv/bin/python -m pytest tests/test_refresh_queue_suggestion_gate_v2_8_e.py tests/test_refresh_queue_historical_sandbox_v2_8_d.py tests/test_source_audit_sandbox_refresh_queue_v2_8_c.py tests/test_live_public_strategy_source_audit_v2_8_b.py tests/test_public_strategy_source_audit_v2_8_a.py tests/test_strategy_research_hypothesis_queue_v2_4_b.py tests/test_historical_sandbox_research_hypotheses_v2_4_c.py tests/test_research_hypotheses_suggestion_gate_v2_4_d.py -q
```

Exit code: `0`

Result: `35 passed in 0.14s`

## SHA256

- `scripts/validate_v2_8_e_refresh_queue_suggestion_gate.py`: `238f9bdfb8e64baf62b7b3140b59bf48c4de90be14e85bb1b1fc1c2499081b15`
- `tests/test_refresh_queue_suggestion_gate_v2_8_e.py`: `e55288a4d4352ab08ea9fef92a720c1eab3761a11726f3010263c648383cfd08`
- `data/reports/v2_8_e_refresh_queue_suggestion_gate_latest.json`: `4fb4f52c328b04936d3cc9bf2cb10734b3278a37bb92aea56dce3d72c3be0399`
- `data/reports/V2_8_E_REFRESH_QUEUE_SUGGESTION_GATE_PASS.marker`: `08e8f8f3c7769b410c7205c385f95683db863e80c5d4196fd07f6da0cbe62b0f`
- `data/processed/v2_8_e_acceptance/v2_8_e_20260711_acceptance/refresh_queue_suggestion_drafts.json`: `7e2d17ea55b81812896b49d7c660759c524bcb1a804af55dede618a29f9fc481`

## Next Target

`V2.8-F Refresh Queue Usable Brief Update`: turn V2.8-E simulation-only drafts
and blocked paths into a user-readable brief without live price, position size,
broker execution, webhook, or production recommendation mutation.

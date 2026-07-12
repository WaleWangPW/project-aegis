# V2.8-F Acceptance Report — Refresh Queue Usable Brief Update

## Result

PASS.

V2.8-F turns the accepted V2.8-E simulation-only suggestion drafts and blocked
paths into a user-readable refresh queue brief. This brief is strategy-basket
level, not concrete-stock level. It does not create live-price advice, position
sizes, orders, broker actions, webhooks, or production `RecommendationRecord`
mutations.

## Command

```bash
.venv/bin/python scripts/validate_v2_8_f_refresh_queue_usable_brief.py --run-id v2_8_f_20260711_acceptance
```

Exit code: `0`

## Evidence

- Report JSON: `data/reports/v2_8_f_refresh_queue_usable_brief_latest.json`
- Report Markdown: `data/reports/v2_8_f_refresh_queue_usable_brief_latest.md`
- Pass marker: `data/reports/V2_8_F_REFRESH_QUEUE_USABLE_BRIEF_PASS.marker`
- Brief JSON: `data/processed/v2_8_f_acceptance/v2_8_f_20260711_acceptance/refresh_queue_usable_brief.json`
- Brief Markdown: `data/processed/v2_8_f_acceptance/v2_8_f_20260711_acceptance/refresh_queue_usable_brief.md`
- Source drafts copy: `data/processed/v2_8_f_acceptance/v2_8_f_20260711_acceptance/source_refresh_queue_suggestion_drafts.json`

## Summary

- Brief items: `6`
- Candidate strategy baskets: `3`
- Blocked paths: `3`
- Candidate markets: `A`, `H`, `US`
- Blocked markets: `A`, `H`, `US`

Candidate strategy baskets:

- `A_LOW_VOL_DIVIDEND_PAPER_BASKET`
- `H_LOW_VOL_DIVIDEND_PAPER_BASKET`
- `US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET`

Blocked paths:

- `A_VALUE_QUALITY_PAPER_BASKET`
- `H_SMART_BETA_PAPER_BASKET`
- `US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET`

## User Boundary

The brief explicitly says:

- It is a simulated strategy-basket brief.
- It is not a concrete stock buy/sell instruction.
- It is not a live order.
- It contains no live price.
- It contains no position size.
- It uses no broker API.
- It uses no trading webhook.
- The user must decide manually outside Aegis.

## Safety Checks

- Has user-readable items.
- Has A/H/US candidate baskets.
- Blocked paths are visible.
- Every item has evidence refs.
- Every item has a plain-language summary.
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
.venv/bin/python -m pytest tests/test_refresh_queue_usable_brief_v2_8_f.py -q
```

Exit code: `0`

Result: `3 passed in 0.07s`

```bash
.venv/bin/python -m pytest tests/test_refresh_queue_usable_brief_v2_8_f.py tests/test_refresh_queue_suggestion_gate_v2_8_e.py tests/test_refresh_queue_historical_sandbox_v2_8_d.py tests/test_source_audit_sandbox_refresh_queue_v2_8_c.py tests/test_live_public_strategy_source_audit_v2_8_b.py tests/test_public_strategy_source_audit_v2_8_a.py tests/test_strategy_research_hypothesis_queue_v2_4_b.py tests/test_historical_sandbox_research_hypotheses_v2_4_c.py tests/test_research_hypotheses_suggestion_gate_v2_4_d.py tests/test_usable_suggestion_brief_v2_6_a.py -q
```

Exit code: `0`

Result: `41 passed in 0.15s`

## SHA256

- `aegis/strategy/refresh_queue_brief.py`: `c76e3d1a7e48ec6625f6723f6c852935dcc655f319cd7ac87e66d04fb92fe597`
- `scripts/validate_v2_8_f_refresh_queue_usable_brief.py`: `d23d85e98fc6da066c5c53ed1df3d4f2fdf7b5086e4957b46163e5e415cc4c35`
- `tests/test_refresh_queue_usable_brief_v2_8_f.py`: `930192ab4beb7c24967ae5ceaad7a17790072ab202fd578ed02ccf425109df83`
- `data/reports/v2_8_f_refresh_queue_usable_brief_latest.json`: `a93770284093eeec8f4d96d319600e78a1406a3fdd310f31d999e7861c6d3cb6`
- `data/reports/V2_8_F_REFRESH_QUEUE_USABLE_BRIEF_PASS.marker`: `55d8ef1da6adf9589e481571a3445363811f637174798296140cccbc768e6199`
- `data/processed/v2_8_f_acceptance/v2_8_f_20260711_acceptance/refresh_queue_usable_brief.json`: `25995136b07ac6aa63c261feed77f92165b582268b45fc223d193fde73068b42`

## Next Target

`V2.8-G Concrete Candidate Binding Refresh`: bind the V2.8-F allowed strategy
baskets to approved concrete A/H/US candidate sources before claiming concrete
stock suggestions. Real user API live dry-run remains pending on non-secret API
metadata and a local env var.

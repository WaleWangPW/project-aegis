# Project Aegis V2.0-B Acceptance Report

Status: `V2.0-B PASS`

Accepted at: `2026-07-11T16:50:23.364990+08:00`

Acceptance target: `V2.0-B Portfolio-Aware Daily Brief`

## What V2.0-B Proves

`V2.0-B Portfolio-Aware Daily Brief` proves that Project Aegis can explain
recommendations against portfolio state without changing the Dashboard
Contract or trading behavior.

The accepted path explains:

- `Action` against cash, exposure, and risk budget.
- `Hold` for an existing watched holding.
- `Wait` for a non-held watched candidate.

This stage is a read-only explanation layer. It does not place trades, connect
to brokers, create webhooks, mutate strategy, or change Dashboard Contract.

## Evidence

- Command: `.venv/bin/python scripts/validate_v2_0_b_portfolio_aware_brief.py --run-id v2_0_b_20260711_acceptance`
- Exit code: `0`
- Marker: `data/reports/V2_0_B_PORTFOLIO_AWARE_BRIEF_PASS.marker`
- Report JSON: `data/reports/v2_0_b_portfolio_aware_brief_latest.json`
- Report Markdown: `data/reports/v2_0_b_portfolio_aware_brief_latest.md`
- Isolated run dir: `data/processed/v2_0_b_acceptance/v2_0_b_20260711_acceptance`
- Dashboard Contract changed: `false`
- Production records written: `false`

## Acceptance Checks

- Recommendations evaluated: `PASS`
- Action explained: `PASS`
- Hold explained: `PASS`
- Wait explained: `PASS`
- Cash, exposure, and risk budget used: `PASS`
- Dashboard Contract unchanged: `PASS`
- No broker or real trade: `PASS`

Summary:

- Recommendation count: `3`
- Portfolio snapshot id: `psnap_20260711_v2_0_a`
- Action counts: `{"hold": 1, "wait": 1, "wait_due_to_portfolio_risk": 1}`

## Hashes

- Report JSON SHA256: `9df32c7c2fb09ab29c81bd948e2bbd92505bc3c6a2864306f1e62fb58829e1bc`
- Report Markdown SHA256: `9e42ee4276a9903b1cd0224a3da35b474ab89236144428590ac1608d390f9c3c`
- Marker SHA256: `7bf27ddbfd24051c1f4106095d7d72f2731823b4972568a563c97f4b470a5502`
- Portfolio JSON SHA256: `11252f2890a7d0f301af3405fa9e4bdc160e70167a0177cc99f0a9f41c05a32d`
- Brief JSON SHA256: `3ec089530c198e2f33bf7c746a38fda167ea3a9808fdcf9d2836d346442b53ba`
- Brief Markdown SHA256: `215e258252931e012b487c5e3655660f06e0ad433c89ef2b76312926769e7b15`

## Safety Boundary

- Read-only explanation layer.
- Simulation only.
- No real trade.
- No broker API.
- No account sync.
- No webhook.
- No auto-rebalance.
- No strategy mutation.
- No Dashboard Contract change.
- No production `data/records` mutation.
- User-submitted external execution facts remain evidence inputs only.

## Next Version Target

After `V2.0-B PASS`, the next product target is `V2.0-C Research Workspace`,
starting with a bounded per-symbol research note and evidence-link model.


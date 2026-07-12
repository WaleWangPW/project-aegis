# V2.9-A Acceptance Report — Current User Decision Packet

## Result

PASS.

V2.9-A creates the current user-facing decision packet from already accepted
evidence. It combines the V2.8-H concrete candidate brief, V2.8-D historical
sandbox results, and V2.8-J API dry-run status into a single readable packet
for manual review and paper/simulation use.

This does not claim live API candidates. The real user API path remains
`blocked_missing_metadata`.

## Command

```bash
.venv/bin/python scripts/validate_v2_9_a_current_user_decision_packet.py --run-id v2_9_a_20260711_acceptance
```

Exit code: `0`

## Evidence

- Report JSON: `data/reports/v2_9_a_current_user_decision_packet_latest.json`
- Report Markdown: `data/reports/v2_9_a_current_user_decision_packet_latest.md`
- Pass marker: `data/reports/V2_9_A_CURRENT_USER_DECISION_PACKET_PASS.marker`
- Decision packet JSON: `data/processed/v2_9_a_acceptance/v2_9_a_20260711_acceptance/current_user_decision_packet.json`
- Decision packet Markdown: `data/processed/v2_9_a_acceptance/v2_9_a_20260711_acceptance/current_user_decision_packet.md`

## Summary

- Simulation candidates: `9`
- Blocked paths: `3`
- Markets: `A`, `H`, `US`
- Sandbox pass count: `3`
- Sandbox fail count: `3`
- Real user API status: `blocked_missing_metadata`

Candidate symbols:

- A: `600519.SH`, `600036.SH`, `601398.SH`
- H: `00700.HK`, `00005.HK`, `00941.HK`
- US: `CRCL`, `MSFT`, `NVDA`

Blocked paths:

- `A_VALUE_QUALITY_PAPER_BASKET`
- `H_SMART_BETA_PAPER_BASKET`
- `US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET`

## User Boundary

The user can now use the packet as a simulation/watchlist review input:

- Review simulation candidates.
- Manually verify live price, liquidity, company events, portfolio conflicts,
  and personal risk budget outside Aegis.
- If the user chooses to trade, execution remains manual in external software.
- Screenshots or typed decisions can be fed back into Aegis as evidence input.

## Safety Checks

- Simulation-only.
- Manual external execution only.
- Fixture candidates are not live market data.
- Real user API remains blocked by missing metadata.
- No live price.
- No position size.
- No real trade.
- No broker API.
- No trading webhook.
- No order placement.
- No production records written.
- Dashboard Contract unchanged.

## Verification

```bash
.venv/bin/python -m pytest tests/test_current_user_decision_packet_v2_9_a.py -q
```

Exit code: `0`

Result: `3 passed in 0.02s`

```bash
.venv/bin/python -m pytest tests/test_current_user_decision_packet_v2_9_a.py tests/test_real_user_api_candidate_refresh_dry_run_v2_8_j.py tests/test_real_user_api_handoff_refresh_v2_8_i.py tests/test_concrete_candidate_usable_brief_v2_8_h.py tests/test_refresh_queue_usable_brief_v2_8_f.py -q
```

Exit code: `0`

Result: `19 passed in 0.12s`

## SHA256

- `scripts/validate_v2_9_a_current_user_decision_packet.py`: `e6febaea4e1698c5bc78c04dbe76d096f0542f84605ebe9bd07a39a04c3076ea`
- `tests/test_current_user_decision_packet_v2_9_a.py`: `47b004794da29ab984c824a413260f9069465f7e3deb76571b3fa87aaa2deac5`
- `data/reports/v2_9_a_current_user_decision_packet_latest.json`: `4b192a55f2b6ba7c9cce54a848d42dcefbaf838772ae3968ef66388a71ccf793`
- `data/reports/V2_9_A_CURRENT_USER_DECISION_PACKET_PASS.marker`: `32fc406c5e69898eebe4418ae34eebac0d0ed8d26ff96146f2dfa16db90a2330`
- `data/processed/v2_9_a_acceptance/v2_9_a_20260711_acceptance/current_user_decision_packet.json`: `9764fa50ea3703a4f811686bc302e031facbc721e728c10f4131ecc2ea6b4fb3`
- `data/processed/v2_9_a_acceptance/v2_9_a_20260711_acceptance/current_user_decision_packet.md`: `02d0e70e070e834f5ff52ebd78e9c9528b7ef0b19dc2ca79e9db782e556b7789`

## Next Target

`V2.9-B User Feedback To Paper Simulation Intake`: let the user mark a packet
item as watch/ignore/manual external action and attach text or screenshot
evidence, still without broker APIs or automatic trading.

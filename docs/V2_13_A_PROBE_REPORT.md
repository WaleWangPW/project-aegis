# V2.13-A Finnhub Free Probe Report

Status: `PASS`

Date: `2026-07-12`

## Result

The Finnhub free probe passed after Codex was restarted and
`AEGIS_FINNHUB_API_KEY` became visible in the active execution environment.

`quote` is reachable on the current key. `social_sentiment` is recorded as
`blocked_plan_or_rate_limit`, which means the endpoint is present but not
available under the current Finnhub plan or rate state. This is acceptable for
V2.13-A because plan-gated sentiment must be recorded, not bypassed.

## Evidence

- Command: `python3 scripts/validate_v2_13_a_finnhub_free_probe.py --run-id v2_13_a_20260712_finnhub_free_probe_rerun`
- Exit code: `0`
- Report JSON: `data/reports/v2_13_a_finnhub_free_probe_latest.json`
- Report MD: `data/reports/v2_13_a_finnhub_free_probe_latest.md`
- Marker: `data/reports/V2_13_A_FINNHUB_FREE_PROBE_PASS.marker`
- Unit tests: `./.venv/bin/pytest tests/test_finnhub_free_probe_v2_13_a.py -q`
- Unit test result: `6 passed`

## Probe Scope

- `quote`: tests whether Finnhub free quote data is reachable for `AAPL`.
- `social_sentiment`: tests whether Finnhub stock social sentiment is reachable
  for `AAPL`.
- Social sentiment may be blocked by Finnhub plan/rate limits. A plan block is
  recorded as evidence and must not be bypassed.

## Safety

- No token values stored.
- No request URL stored.
- No raw payload stored.
- No production record written.
- No Dashboard Contract change.
- No real trade.
- No broker API.
- No trading webhook.
- No order placement.

## Next Step

Proceed to `V2.13-B Finnhub Metadata Activation`.

Metadata activation may use Finnhub quote as a free reachable endpoint. It must
keep social sentiment as `blocked_plan_or_rate_limit` until the plan is upgraded
or Finnhub grants access.

# V2.4-C Acceptance Report

## Result

- Target: `V2.4-C Historical Sandbox Run For Research Hypotheses`
- Status: `PASS`
- Run ID: `v2_4_c_20260711_acceptance`
- Acceptance command:
  - `.venv/bin/python scripts/validate_v2_4_c_historical_sandbox_research_hypotheses.py --run-id v2_4_c_20260711_acceptance`
- Exit code: `0`
- Related regression:
  - `106 passed`

## What Passed

`V2.4-C` converted the `V2.4-B` A/H/US research hypothesis queue into isolated historical sandbox candidates and historical cases. It then ran a bounded simulation-only evaluation before allowing any path toward user-facing suggestion drafts.

Summary:

- Hypotheses evaluated: `6`
- Historical cases: `24`
- Passing hypotheses: `3`
- Failing hypotheses: `3`
- Historical cache files detected: `222`

Passing hypotheses:

- `hyp_a_low_vol_dividend_defensive`
- `hyp_h_low_vol_dividend`
- `hyp_us_value_quality_momentum`

Failing hypotheses:

- `hyp_a_value_quality_multifactor`
- `hyp_h_smart_beta_multifactor`
- `hyp_us_low_vol_risk_overlay`

Observed failure reasons include:

- `average_return_below_threshold`
- `max_drawdown_breached`
- `win_rate_below_threshold`

## Evidence

- `data/reports/V2_4_C_HISTORICAL_SANDBOX_RESEARCH_HYPOTHESES_PASS.marker`
- `data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.json`
- `data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.md`
- `data/processed/v2_4_c_acceptance/v2_4_c_20260711_acceptance/hypothesis_sandbox_report.json`
- `data/processed/v2_4_c_acceptance/v2_4_c_20260711_acceptance/hypothesis_strategy_candidates.json`
- `data/processed/v2_4_c_acceptance/v2_4_c_20260711_acceptance/hypothesis_historical_strategy_cases.jsonl`

SHA256:

- `1f85d14ab1d4921f1dc7f73247f0c89ac9d6b4937d8ea51ad740b209ec30cafb` `aegis/strategy/hypothesis_sandbox.py`
- `7b5bb5acb7746a4238c25dfc30905c51d022a748dd8397f2ea63548635d76239` `scripts/validate_v2_4_c_historical_sandbox_research_hypotheses.py`
- `2d5a0eef93042b40533a59885ae26feabd6e79c475da99fce3754537e2df0f48` `tests/test_historical_sandbox_research_hypotheses_v2_4_c.py`
- `5590109b0fd3c46d27b53425d8675bb625f68d971a137be0f357ed03e0892309` `data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.json`
- `822bd2408dc76728645b048badb1ee853cf2f061f7d3009c64e927f605386e38` `data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.md`
- `56e375d9de5756b682919ceb7e95c63b92e263eb4b62bee95e23b41f59cdde0c` `data/reports/V2_4_C_HISTORICAL_SANDBOX_RESEARCH_HYPOTHESES_PASS.marker`
- `f24e365814d6d17ab9b3bdac896b062bc57d28a3e1da96ec465a878e89faaf2e` `data/processed/v2_4_c_acceptance/v2_4_c_20260711_acceptance/hypothesis_sandbox_report.json`
- `b225c74ac4b6caf19f3080caaf3e321e2785a7da17f389fe6b8f90edeb2d3f12` `data/processed/v2_4_c_acceptance/v2_4_c_20260711_acceptance/hypothesis_strategy_candidates.json`
- `b0f10aba635fc56cedae7930227a760a6780de9381000b2b6b20a3f92bc69610` `data/processed/v2_4_c_acceptance/v2_4_c_20260711_acceptance/hypothesis_historical_strategy_cases.jsonl`

## Safety Boundary

This acceptance remains research and simulation only.

- No real trade
- No broker API
- No trading webhook
- No secret storage
- No production recommendation records mutated
- No strategy auto-mutation
- Dashboard Contract unchanged
- Suggestion Gate still required

Passing hypotheses are not user-facing suggestions yet. The next target should route only passing hypotheses into bounded suggestion drafts through the existing Suggestion Gate and risk checks.


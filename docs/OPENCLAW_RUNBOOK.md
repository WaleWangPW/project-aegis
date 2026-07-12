# Project Aegis OpenClaw Runbook

OpenClaw is the default execution entry for Project Aegis routine work. Codex remains the reviewer for file edits, high-risk choices, contract changes, and acceptance disputes.

## Start Here

Read these files in order:

1. `docs/ROADMAP.md`
2. `docs/HANDOFF.md`
3. `docs/OPENCLAW_RUNBOOK.md`
4. `docs/context/00_CHATGPT_CONTEXT.md` only if a historical P25.6 snapshot is needed

Current baseline:

- Accepted stage: `P25.6 PASS`
- Product version: `V2.5-C User API Live Candidate Refresh PASS`
- Scope decision: `docs/V2_0_SCOPE_DECISION.md`
- Next target: `V2.6-A Usable Suggestion Brief`
- Dashboard Contract: `2.0`
- Production Dashboard SHA256: `e777047e93fc13705df2e6c0dd58728c12ed97ee3f338b512d26ae84b1897a41`

## Allowed Work

OpenClaw may do routine, bounded, evidence-producing work:

- Read project state, roadmap, handoff, and reports.
- Run approved read-only or dry-run scripts.
- Run already-approved status refresh commands when the task envelope explicitly allows it.
- Collect command, exit code, artifact paths, marker paths, report paths, and SHA256 hashes.
- Summarize findings in compact form for Codex or the user.
- Prepare evidence packets for the next approved version target.

Allowed work must stay inside the existing project boundary and must not change strategy, contract, dashboard logic, or trading behavior.

## Forbidden Work

OpenClaw must not:

- Place real trades or simulate approval for real trades.
- Connect to a broker or broker API.
- Create trading webhooks.
- Read, print, copy, or store secrets.
- Modify Decision Engine thresholds, Expert Agent logic, Risk Engine logic, Provider routing policy, Dashboard Contract, Evidence Gate, or tests.
- Edit `dashboard/index.html` or contract artifacts unless a separate approved task says so.
- Delete or rewrite audit records such as `data/records/*.jsonl`.
- Treat `PASS` markers as sufficient evidence without checking exit code, freshness, and hashes.
- Invent recommendations, prices, returns, reviews, or memory entries.

## Evidence Rules

Every OpenClaw run must return:

- Goal
- Scope
- Non-goals
- Commands run
- Exit code for each command
- Output artifact paths
- Marker/report paths
- SHA256 hashes for contract or dashboard artifacts when relevant
- Evidence status: `passed`, `failed`, `blocked`, or `not verified`
- Blockers and escalation reason

Evidence standard:

- Evidence is stronger than claim.
- Exit code must be checked.
- Hashes must be checked when files are part of acceptance.
- Marker files are supporting evidence only; never accept marker-only PASS.
- If evidence is stale or missing, report `not verified`.

## Escalation Rules

Escalate to Codex when any of these happen:

- Exit code is non-zero.
- Expected artifact is missing.
- Hash differs from the accepted baseline.
- Evidence report is stale or internally inconsistent.
- A task touches strategy, dashboard contract, Evidence Gate, tests, security, secrets, broker access, or real trading.
- A run would overwrite known high-risk reports without an explicit disposable output path.
- The next step requires a new version target or new acceptance gate.

OpenClaw should stop after two repeated failures of the same task and return a concise blocked report.

## Output Template

Use this shape for every run:

```text
Project: Project Aegis
Target: <version or stage>
Goal:
Scope:
Non-goals:
Commands:
- <command> -> exit_code=<code>
Artifacts:
- <path>
Hashes:
- <path> sha256=<hash>
Evidence status: passed|failed|blocked|not verified
Blockers:
Escalation needed: yes|no
Next suggested action:
```

## Current Next Target

`V1.0 Review/Memory single-cycle acceptance` is accepted. Evidence:

- `docs/V1_0_ACCEPTANCE_REPORT.md`
- `data/reports/V1_0_SINGLE_CYCLE_ACCEPTANCE_PASS.marker`
- `data/reports/v1_0_single_cycle_acceptance_latest.json`

`V1.5 Review System` is accepted. Evidence:

- `docs/V1_5_ACCEPTANCE_REPORT.md`
- `data/reports/V1_5_REVIEW_SYSTEM_PASS.marker`
- `data/reports/v1_5_review_system_acceptance_latest.json`

`V2.0-A` through `V2.0-F` are accepted. Evidence is listed in
`docs/HANDOFF.md`.

`V2.1-A Historical Strategy Sandbox` is accepted. Evidence:

- `docs/V2_1_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_1_A_HISTORICAL_STRATEGY_SANDBOX_PASS.marker`
- `data/reports/v2_1_a_historical_strategy_sandbox_latest.json`

`V2.1-B Strategy Candidate Library` is accepted. Evidence:

- `docs/V2_1_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_1_B_STRATEGY_CANDIDATE_LIBRARY_PASS.marker`
- `data/reports/v2_1_b_strategy_candidate_library_latest.json`

`V2.1-C Suggestion Gate` is accepted. Evidence:

- `docs/V2_1_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_1_C_SUGGESTION_GATE_PASS.marker`
- `data/reports/v2_1_c_suggestion_gate_latest.json`

`V2.2-A External API Connector and Strategy Research Ingestion` is accepted.
Evidence:

- `docs/V2_2_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_2_A_EXTERNAL_API_RESEARCH_INGESTION_PASS.marker`
- `data/reports/v2_2_a_external_api_research_ingestion_latest.json`

`V2.2-B API-backed Research Fetch Dry Run` is accepted. Evidence:

- `docs/V2_2_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_2_B_API_BACKED_RESEARCH_FETCH_PASS.marker`
- `data/reports/v2_2_b_api_backed_research_fetch_latest.json`

`V2.2-C API Research To Sandbox Candidate Bridge` is accepted. Evidence:

- `docs/V2_2_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_2_C_API_RESEARCH_BRIDGE_PASS.marker`
- `data/reports/v2_2_c_api_research_bridge_latest.json`

`V2.3-A Real User API Configuration Handoff` is accepted. Evidence:

- `docs/V2_3_A_ACCEPTANCE_REPORT.md`
- `docs/API_CONFIGURATION_HANDOFF.md`
- `data/reports/V2_3_A_API_CONFIGURATION_HANDOFF_PASS.marker`
- `data/reports/v2_3_a_api_configuration_handoff_latest.json`

`V2.3-B Real User API Dry Run Entrypoint` is accepted. Evidence:

- `docs/V2_3_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_3_B_REAL_USER_API_DRY_RUN_PASS.marker`
- `data/reports/v2_3_b_real_user_api_dry_run_latest.json`

`V2.3-C Live API Dry Run After User Provides Metadata` is pending user input.
OpenClaw may run the bounded dry-run command only after non-secret connector
metadata exists and the required env var is already set locally outside the
repo/Vault. OpenClaw must not print, copy, store, or request API key values,
and the live dry-run still cannot mutate strategy definitions, produce direct
user-facing suggestions, touch Dashboard Contract, connect a broker, or create
trading webhooks.

`V2.4-A Strategy Research Source Catalog` is accepted. Evidence:

- `docs/V2_4_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_4_A_STRATEGY_RESEARCH_SOURCE_CATALOG_PASS.marker`
- `data/reports/v2_4_a_strategy_research_source_catalog_latest.json`

`V2.4-B Strategy Research To Sandbox Hypothesis Queue` completed the next
no-secret step after this source catalog. OpenClaw may inspect the summary-only
hypothesis artifacts, but must not auto-apply strategy changes, generate direct
user-facing suggestions, bypass historical sandbox, or bypass Suggestion Gate.
`V2.3-C Live API Dry Run After User Provides Metadata` remains pending until
the user provides non-secret metadata and local env var setup.

`V2.4-B Strategy Research To Sandbox Hypothesis Queue` is accepted. Evidence:

- `docs/V2_4_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_4_B_STRATEGY_RESEARCH_HYPOTHESIS_QUEUE_PASS.marker`
- `data/reports/v2_4_b_strategy_research_hypothesis_queue_latest.json`

`V2.4-C Historical Sandbox Run For Research Hypotheses` is accepted. Evidence:

- `docs/V2_4_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_4_C_HISTORICAL_SANDBOX_RESEARCH_HYPOTHESES_PASS.marker`
- `data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.json`

`V2.4-D Research Hypotheses To Suggestion Gate Drafts` is accepted. Evidence:

- `docs/V2_4_D_ACCEPTANCE_REPORT.md`
- `data/reports/V2_4_D_RESEARCH_HYPOTHESES_SUGGESTION_GATE_PASS.marker`
- `data/reports/v2_4_d_research_hypotheses_suggestion_gate_latest.json`

`V2.5-A Approved Candidate Binding For Suggestion Drafts` is accepted.
Evidence:

- `docs/V2_5_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_5_A_APPROVED_CANDIDATE_BINDING_PASS.marker`
- `data/reports/v2_5_a_candidate_binding_latest.json`

`V2.5-B Approved Live Candidate Refresh` is accepted. Evidence:

- `docs/V2_5_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_5_B_APPROVED_CANDIDATE_REFRESH_PASS.marker`
- `data/reports/v2_5_b_candidate_refresh_latest.json`

`V2.5-C User API Live Candidate Refresh` is accepted in fixture mode. Evidence:

- `docs/V2_5_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_5_C_USER_API_CANDIDATE_REFRESH_PASS.marker`
- `data/reports/v2_5_c_user_api_candidate_refresh_latest.json`

The next target is `V2.6-A Usable Suggestion Brief`. OpenClaw may prepare a
user-readable simulation-only brief from current evidence-labeled candidates.
Real user API live refresh can be rerun only after non-secret connector metadata
exists and the required env var is already set locally outside the repo/Vault.
OpenClaw must not print/store secrets, connect a broker, create a trading
webhook, bypass risk veto, or treat candidates as final buy/sell instructions.

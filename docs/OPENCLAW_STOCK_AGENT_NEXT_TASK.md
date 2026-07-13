# Project Aegis OpenClaw Stock-Agent Next Task

Updated At: 2026-07-13T11:45:00+08:00

## Objective

Continue A-share Tushare strategy validation upstream of the suggestion gate.
The goal is to improve historical evidence quality for moneyflow, dragon-tiger,
hot-money, ownership, and factor strategies.

This task must not create user-facing recommendations while the gate is closed.

## Current Gate Snapshot

Latest managed cycle evidence:

- `generated_at=2026-07-13T11:25:54+08:00`
- `overall_exit_code=0`
- `report_sha256=f581dffbadf9b8bc8aa8edaecd8a82a9e1064f4a49976fcb5c88000563274f9c`
- `refined_sandbox_pass_candidate_count=0`
- `ranking_gate_reviewed_count=0`
- `ranking_gate_approved_count=0`
- `user_facing_suggestion_allowed=false`
- `deep_sandbox_fail_count=5`
- `tuned_fail_count=4`
- `strategy_priority_action_count=1`
- `full_year_coverage_answer=NO`
- `strategy_experiment_queue_ready_count=6`
- `full_year_coverage_status=WAITING_CURRENT_TRADING_DAY_DAILY`

Interpretation: Aegis can show strategy research status, but cannot promote any
A-share strategy into Dashboard recommendation ranking.

## Approved Command

Run from the Project Aegis repo:

```bash
make stock-agent-a-share-strategy-cycle-managed-expanded
```

This is the approved bounded cycle for the current A-share strategy work. It
keeps dragon-tiger and hot-money data as research-only samples and writes
derived evidence reports.

## Current Next Focus

The latest managed-expanded cycle produced no ranking-gate candidate. The next
useful work is not to relax the gate, but to improve upstream evidence:

1. Review the six ready experiment-queue items in
   `data/reports/a_share_strategy_experiment_queue_latest.json`.
2. Retry the A-share full-year cross-section cache after Tushare publishes the
   current trading day's daily data. The current blocker is
   `current_trading_day_daily_not_yet_available` for `20260713`, not a broad
   missing-history issue.
3. After cache freshness is no longer waiting/stale, rerun the approved managed-expanded
   cycle and compare whether deep sandbox failures and tuned failures improve.

## Allowed

- Use the local Tushare API through existing project scripts.
- Read local historical cache and derived strategy reports.
- Write local derived cache/report artifacts needed by the sandbox.
- Collect command, exit code, report path, marker path, SHA256, and summary
  counts.
- Propose the next bounded stock-agent task if the gate remains blocked.

## Forbidden

- Do not read, print, copy, or store API keys or secrets.
- Do not connect to any broker API.
- Do not place real orders.
- Do not create or call trading webhooks.
- Do not modify Dashboard Contract, Evidence Gate, tests, or trading safety
  rules.
- Do not bypass `ranking_gate_approved_count`.
- Do not claim an A-share strategy is recommendable while
  `user_facing_suggestion_allowed=false`.

## Required Output

Return a compact evidence packet:

```text
Project: Project Aegis
Agent: OpenClaw stock-agent
Goal:
Command:
- make stock-agent-a-share-strategy-cycle-managed-expanded -> exit_code=<code>
Reports:
- <path> sha256=<hash>
Key counts:
- refined_sandbox_pass_candidate_count=<n>
- ranking_gate_reviewed_count=<n>
- ranking_gate_approved_count=<n>
- user_facing_suggestion_allowed=<true|false>
- deep_sandbox_fail_count=<n>
- tuned_fail_count=<n>
Evidence status: passed|failed|blocked|not verified
Blockers:
Next suggested action:
Safety: simulation-only; no broker; no real order; no webhook; no secrets.
```

## Acceptance Gate

Only Codex may accept a strategy as usable for Dashboard recommendation ranking.
The minimum evidence condition is:

- `ranking_gate_approved_count > 0`
- `user_facing_suggestion_allowed=true`
- Exit code is `0`
- Report hashes are recorded
- No safety boundary was touched

Until then, Aegis may display research status only.

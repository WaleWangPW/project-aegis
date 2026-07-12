# Project Aegis Dashboard UI Spec

Status: `ready for UI redesign`
Updated At: `2026-07-12`

This spec describes the current Dashboard surface for UI design. It does not
change Dashboard Contract `2.0`, Evidence Gate, Pipeline, strategy logic, or
simulation-only safety boundaries.

## Purpose

The Dashboard is the daily decision surface for Project Aegis. It should let the
user understand the day in under 5 minutes:

- Can I do anything today?
- What risk blocks action?
- Which candidates deserve simulation research?
- Which candidates have been downgraded by historical evidence?
- What evidence backs the answer?

## Fixed Safety Boundary

The Dashboard must remain read-only and simulation-only.

Forbidden UI controls:

- Real trade.
- Buy/sell/order.
- Broker API connection.
- Trading webhook.
- Secrets/API key entry.
- Position sizing as an executable instruction.

Allowed UI controls:

- Refresh local data.
- Expand details.
- View evidence reports.
- Record or display simulation-only feedback.

## Current Page Structure

1. Status strip.
2. Today conclusion.
3. Today stock selection workbench.
4. Risk blockers.
5. Holdings/watch objects.
6. Watchlist.
7. Market status.
8. Next check.
9. Historical backtest and case evaluation.
10. System and evidence details.

Mobile order should preserve the same priority, with all secondary sections
collapsed by default.

## Current Data Reports

| Section | Source |
| --- | --- |
| System strip | `aegis_health_status_latest.json` |
| Today conclusion | derived in `dashboard/v2.js` from health, gate, daily, risk and watchlist reports |
| Stock selection | `stock_selection_workbench_latest.json` |
| Feedback confirmation | `aegis_stock_feedback_latest.json` |
| Risk blockers | `crcl_risk_monitor_latest.json`, `000002.sz_risk_monitor_latest.json` |
| Historical cases | `aegis_strategy_specific_historical_cases_latest.json` |
| Case evaluation | `aegis_strategy_specific_case_evaluation_latest.json` |
| Evidence details | `aegis_evidence_gate_latest.json`, pipeline/audit reports |

## Current Design Baseline

Current page is usable and data-backed, but text density remains high. Design
work should optimize hierarchy and scanning rather than add features.

Current evidence counters:

- Candidate workbench: 30 total candidates, 13 research candidates.
- News enrichment: 9 candidates.
- Historical cases: 52.
- Data gaps: 0.
- Case evaluation: 8 continue simulation research, 2 watch-only, 3 downgraded.

## Recommended Visual Direction

Use `Soft Structuralism + Asymmetrical Bento`.

Design principles:

- Large first-read decision block.
- Evidence board instead of raw tables.
- Candidate cards with clear "why / risk / news / case result".
- Double-bezel card construction for premium structure.
- Warm light background; avoid generic dark trading terminal.
- Motion only through transform and opacity.

## Component Inventory

### Status Strip

Must show date, system status, data update time, auto-check result, and refresh
button. It should feel like an instrument cluster, not a navbar.

### Today Conclusion

Must dominate the first screen. States:

- Risk-first.
- Blocked.
- Ready.
- Watch/review.
- No data.

Must include:

- Allowed action.
- Forbidden action.
- Risk count.
- Action count.
- Next check.

### Candidate Card

Must include:

- Market pill.
- Symbol and company name.
- Price, daily change, one-year change.
- Strategy reason.
- Latest news summary in Chinese where available.
- Risk flags.
- Case evaluation disposition.
- Simulation-only action boundary.

### Case Evaluation Board

Must include:

- 52 historical cases.
- 0 data gaps.
- 8 continue simulation research.
- 2 watch only.
- 3 downgraded.
- Strongest candidates.
- Watch-only and downgraded candidates.
- Historical result disclaimer.

### Evidence Details

Must remain accessible but not visually dominate the main daily flow.

## Required Empty/Error States

- Missing report.
- Missing news.
- No research candidates.
- Evidence Gate fail.
- System health fail.
- Risk veto active.
- Case evaluation unavailable.

Every missing state must degrade to natural language and must not invent values.

## Design-Ready References

- Main design starter: `docs/UI_DESIGN_STARTER.md`
- Version visual brief: `docs/VERSION_VISUAL_BRIEF.md`
- Strategy research: `docs/STRATEGY_RESEARCH.md`
- Current dashboard files: `dashboard/index.html`, `dashboard/v2.css`,
  `dashboard/v2.js`

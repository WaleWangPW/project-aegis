# Project Aegis UI Design Starter

Status: `ready for UI design kickoff`
Updated At: `2026-07-12`
Scope: Project Aegis dashboard and stock-assistant presentation surfaces only.

This document is the design handoff for Canva/Figma/UI redesign work. It does
not change trading logic, Dashboard Contract, Pipeline, Evidence Gate, strategy
rules, or data providers.

## Product State

Aegis is a stock research and simulation system. It helps the user screen
A/HK/US stocks, read risk and evidence, record simulation-only feedback, and
review historical case performance. It does not place real trades.

Current usable page:

- Local URL: `http://localhost:8080/dashboard/index.html`
- Dashboard Contract: `2.0`
- Current JS/CSS cache version: `20260712h`
- Current page title: `Project Aegis · 每日决策`

Current data baseline:

- Stock workbench: 30 total candidates, 13 research candidates, 11 high-risk
  watch, 6 blocked, 9 with news enrichment.
- Strategy-specific historical cases: 13/13 candidates covered, 52 cases, 0
  data gaps.
- Case evaluation: 8 simulation research candidates, 2 watch-only candidates,
  3 downgraded candidates.
- Safety: simulation only; no broker API, no webhook, no order placement, no
  position sizing, no live order signal.

## Design Goal

Make Aegis feel like a daily investment command room that can be understood in
5 minutes:

1. What should I do today?
2. What risks block action?
3. Which candidates deserve simulation research?
4. Which candidates were downgraded by historical evidence?
5. What evidence and feedback are behind the decision?

The design should reduce text density, create stronger hierarchy, and make the
system feel reliable without making it look like a trading terminal.

## Non-Goals

- No real trading UI.
- No buy/sell/order buttons.
- No broker connection flow.
- No webhook controls.
- No secrets, token screens, or API-key exposure.
- No composite score as the final decision.
- No dark-pattern language implying guaranteed returns.

## Recommended Visual Direction

Use `Soft Structuralism + Asymmetrical Bento`.

Rationale:

- The current product is data-heavy and high-trust; a calm light interface is
  easier to read daily than a dense dark terminal.
- Bento cards can separate decision, risk, candidates, and evidence without
  turning everything into a table.
- A premium, quiet visual system fits a personal decision OS better than a
  gamified trading app.

Suggested aesthetic:

- Background: warm off-white / silver-grey canvas with subtle gradient wash.
- Typography: expressive grotesk for UI labels, editorial serif only for large
  decision headlines if needed. Avoid default system look.
- Components: double-bezel cards, soft trays, nested status pills, generous
  white space.
- Motion: slow page-load reveal, drawer expansion, candidate card focus
  transitions using transform/opacity only.

Suggested tokens:

| Token | Value |
| --- | --- |
| `--bg` | `#f4f1e8` |
| `--surface` | `#fffdf7` |
| `--surface-soft` | `#ebe7dc` |
| `--ink` | `#181713` |
| `--muted` | `#6e6a5f` |
| `--good` | `#1f7a4d` |
| `--warn` | `#9b6a12` |
| `--risk` | `#b13a2f` |
| `--line` | `rgba(24,23,19,0.10)` |
| `--radius-xl` | `32px` |
| `--ease-out-heavy` | `cubic-bezier(0.32,0.72,0,1)` |

## Information Architecture

### Primary Screen: Daily Decision

Purpose: the default page the user opens every day.

Priority order:

1. System strip: date, system health, data time, auto-check status.
2. Today conclusion: action permission and forbidden action.
3. Today stock selection: top candidates and simulation-only boundary.
4. Risk blockers: holdings or watch items requiring review.
5. Strategy case evaluation: continue research / watch only / downgraded.
6. Evidence details: reports, hashes, source links, unavailable data.

### Candidate Card

Each candidate card should answer:

- Market and symbol.
- Company one-liner.
- Current price, daily move, one-year move.
- Why it entered the candidate set.
- Latest news summary in Chinese.
- Risk note.
- Historical case disposition.
- Allowed user action: `加入模拟观察`, `暂不关注`, `要更多资讯`.

Candidate card must never say "buy", "sell", "execute", or "order".

### Historical Evidence Drawer

This should be redesigned as a compact evidence board:

- `52` historical cases.
- `0` data gaps.
- `8` continue simulation research.
- `2` watch only.
- `3` downgraded.
- Lists for strongest candidates and downgraded candidates.
- Clear note: historical result is not real future performance.

### Feedback State

The UI should show a small confirmation state after feedback:

- Last feedback symbol.
- Action received.
- Timestamp.
- Boundary copy: "只记录研究反馈，不创建纸面交易、不改持仓、不调用券商、不下单。"

## Current Surface Inventory

| Surface | Current File | Design Status |
| --- | --- | --- |
| Daily dashboard | `dashboard/index.html`, `dashboard/v2.css`, `dashboard/v2.js` | Ready for redesign |
| Dashboard UI spec | `dashboard/v2_ui_spec.md` | Expanded for design |
| Product version visuals | `docs/VERSION_VISUAL_BRIEF.md` | Existing concept boards |
| Version SVGs | `docs/visuals/*.svg` | Existing approval visuals |
| Strategy research | `docs/STRATEGY_RESEARCH.md` | Data/strategy source for UI copy |
| Stock assistant cards | `data/reports/aegis_stock_assistant_feishu_cards_latest.json` | Needs redesign after dashboard direction |

## Data Inputs For Design

Design should use real report fields, not invented sample content.

| UI Need | Source Report |
| --- | --- |
| System health | `aegis_health_status_latest.json` |
| Evidence pass/fail | `aegis_evidence_gate_latest.json` |
| Daily checks | `aegis_daily_dry_run_hardened_latest.json` |
| Candidate workbench | `stock_selection_workbench_latest.json` |
| Historical cases | `aegis_strategy_specific_historical_cases_latest.json` |
| Case evaluation | `aegis_strategy_specific_case_evaluation_latest.json` |
| User feedback | `aegis_stock_feedback_latest.json` |
| Risk monitors | `crcl_risk_monitor_latest.json`, `000002.sz_risk_monitor_latest.json` |

## Required States

The UI design must cover:

- Normal.
- Risk-first day.
- No actionable candidate.
- Candidate available for simulation research.
- Watch-only candidate.
- Downgraded candidate.
- Missing news.
- Missing report.
- Evidence Gate failure.
- Mobile portrait view.

## Copy Rules

Use these terms:

- `继续模拟研究`
- `只观察`
- `降级`
- `风险阻塞`
- `证据`
- `回传已记录`
- `不真实交易`

Avoid these terms:

- `买入`
- `卖出`
- `下单`
- `自动交易`
- `稳赚`
- `AI 自学习交易`
- `券商连接`

## Design Deliverables To Create Next

1. `Dashboard Daily Command` desktop mock.
2. `Mobile Daily Brief` mock.
3. `Candidate Card System` mock.
4. `Historical Evidence Board` mock.
5. `Stock Assistant Push Card` mock for Feishu/OpenClaw.

Each mock should include a safety footer:

> 仅模拟研究。Aegis 不接券商、不下单、不调用交易 webhook。

## Start Criteria

UI design can start when all of these are true:

- Dashboard local URL returns `200`.
- `dashboard/v2.js` syntax check passes.
- Stock workbench report exists.
- Strategy-specific historical cases report exists.
- Case evaluation report exists.
- The safety boundary is visible in the UI or design brief.

Current status: all criteria above are satisfied as of `2026-07-12`.

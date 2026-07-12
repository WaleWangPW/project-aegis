# Project Aegis V2.0 Scope Decision

Status: `proposed`

Decision date: `2026-07-11`

Recommended direction: `Portfolio-first`

## Product Position

Project Aegis is a personal stock investment decision and review system. V2.0
should turn it from a dashboard plus review loop into a personal investment
operating workspace.

V2.0 must stay inside the existing safety boundary:

- No real trading.
- No Broker API.
- No webhook trading.
- No secrets in repo or Vault.
- No automatic strategy mutation from AI or review data.
- No multi-user, SaaS, public API, or enterprise workflow.

Real-world execution boundary:

- The user may place real orders manually in another application.
- Aegis must never place, route, approve, or simulate approval for those real
  orders.
- Aegis may receive user-submitted execution facts after the fact, such as
  screenshots, typed fills, manual notes, or copied broker statements.
- User-submitted execution facts are evidence inputs only. They do not give
  Aegis permission to connect to a broker or execute trades.

## Decision

Start V2.0 with `Portfolio-first`.

Reason:

- A stock system needs to understand current holdings, cash, exposure, and risk
  budget before research notes can become useful decisions.
- V1.0 already proves a single recommendation can reach Review and Investment
  Memory. V1.5 already proves periodic review. The missing operating layer is
  portfolio state.
- Research Workspace is valuable, but without portfolio context it risks
  becoming a notes database rather than a decision system.

## V2.0 Phase Order

### V2.0-A: Portfolio Foundation

Goal: create a read-only portfolio model for personal decision support.

Must include:

- Holdings record.
- Cash record.
- Position sizing fields.
- Exposure summary.
- Risk budget summary.
- Portfolio snapshot report.
- Hashable evidence output.
- Clear separation between simulated trades and user-submitted external
  execution facts.

Must not include:

- Real orders.
- Broker connection.
- Account sync.
- Secrets.
- Auto-rebalance.
- Automatic buy/sell execution.
- Reading screenshots with hidden secrets or account credentials.

Acceptance gate:

- A deterministic fixture portfolio can produce a portfolio snapshot.
- Snapshot includes holdings, cash, exposure, risk budget, and blockers.
- Command exits `0`.
- Report path and SHA256 are recorded.
- Production records are not mutated unless explicitly approved.

### V2.0-B: Portfolio-Aware Daily Brief

Goal: daily recommendations can be explained against current portfolio state.

Must include:

- Whether a recommendation conflicts with current exposure.
- Whether cash is sufficient.
- Whether risk budget allows the action.
- Why not increase position now.
- Why hold or wait.

Must not include:

- Dashboard Contract change unless separately approved.
- Strategy change.
- Broker or order workflow.

Acceptance gate:

- At least one recommendation is evaluated with portfolio context.
- Output explains action/hold/wait using cash, exposure, and risk budget.
- Evidence includes command, exit code, artifact path, and hash.

### V2.0-C: Research Workspace

Goal: add per-symbol research only after portfolio context exists.

Must include:

- Symbol profile.
- Research notes.
- Evidence links.
- Timeline references.
- Decision-relevant summary.

Must not include:

- General knowledge-base sprawl.
- LLM-generated unverified facts as evidence.
- News ingestion that bypasses Evidence Gate.

### V2.0-D: Event Timeline and Scenarios

Goal: add event and scenario context after portfolio and research foundations.

Possible scope:

- Earnings and announcement timeline.
- Industry or macro event notes.
- Scenario impact summary.
- Why now / why not now explanation.

## Not V2.0

These stay outside V2.0:

- Natural language analyst chat.
- AI proactive opportunity hunting.
- Multi-strategy auto-switching.
- Reinforcement learning.
- Neural network prediction.
- Multi-user collaboration.
- SaaS or public API.
- Real trading.
- Broker login, cookie capture, or account scraping.

## Open Approval Items

The recommended default is:

- First build `V2.0-A Portfolio Foundation`.
- Keep V1.5 Review Console as a separate review surface for now.
- Keep the visual style dark and evidence-command oriented for operating
  screens, while allowing lighter research-note surfaces later.
- Keep V3.0 natural-language analyst as future read-only Q&A, not current V2.0.

## Next Implementation Target

If approved, the next engineering target is:

`V2.0-A Portfolio Foundation acceptance`

Expected output:

- Portfolio data model.
- Portfolio snapshot builder.
- Isolated acceptance validator.
- Targeted tests.
- Acceptance report and PASS/FAIL marker.

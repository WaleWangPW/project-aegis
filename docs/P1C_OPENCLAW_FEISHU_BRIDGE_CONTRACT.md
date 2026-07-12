# Project Aegis — P1C OpenClaw/Feishu Bridge Contract

Produced per `Claude_Cowork_P1B4_1_THEN_P1C_DESKTOP_READONLY.md`, Step 2.
This document is the binding contract for how OpenClaw, Feishu, or any
other external agent/automation is allowed to interact with Project
Aegis. Project Aegis's own OpenClaw/Feishu bridge implementation (the
actual OpenClaw skill/Feishu bot wiring) is **not** built in this round —
this round only builds the read-only surface (`scripts/aegis_agent_gateway.py`
+ `data/desktop/aegis_status.html`) that such a bridge would call. No
broker integration, no real trading, and no composite/weighted scoring
exist anywhere in this repo, in this round or any prior round.

## The single entry point

OpenClaw (or any other external agent) may call **only**:

```
scripts/aegis_agent_gateway.py
```

No other script, module, or file in this repository is an approved
integration surface for an external agent. In particular:

- OpenClaw must **not** import `aegis.*` modules directly and call them
  itself — it must go through the gateway CLI (or a future thin wrapper
  around the exact same `dispatch()` function), so every access is
  auditable through one code path.
- OpenClaw must **not** directly edit any `.jsonl` record file under
  `data/records/` (`recommendations.jsonl`, `decisions.jsonl`,
  `paper_trades.jsonl`, `reviews.jsonl`, `data_gaps.jsonl`). All of
  those are written only by their respective Aegis services
  (`RecommendationService`, `PaperTradeService`, `ReviewService`,
  `DataGapRegistry`), never by an external agent.
- OpenClaw must **not** read `.env` or any token value, directly or
  indirectly. The gateway itself never imports a provider adapter or
  touches `os.environ`/`dotenv` — every gateway command only reads
  already-persisted JSON/JSONL/YAML files.
- OpenClaw must **not** create `PaperTrade` records. There is no gateway
  command that creates one; `paper-buy`/`paper-sell`/`create-paper-trade`
  are explicitly in the forbidden-command list and are refused with a
  structured JSON error and a non-zero exit code.
- OpenClaw must **not** call any broker API. No broker integration
  exists anywhere in Project Aegis (Master Spec ADR-004: "never a real
  brokerage order"), so there is nothing for OpenClaw to call even if it
  tried; `broker`/`auto-trade`/`trade`/`order`/`buy`/`sell`/`rebalance`
  are all explicitly forbidden gateway commands regardless.
- Feishu is a **read-only query/notification interface only**. A Feishu
  bot built on top of this bridge may answer questions ("what are my
  holdings", "what's the latest recommendation", "any data gaps") and
  may push notifications, but must never accept a command from a Feishu
  user that results in a trade, a PaperTrade, or a Decision/Recommendation
  mutation — the gateway itself enforces this by refusing those commands
  outright, so even a compromised or misconfigured Feishu bot cannot
  bypass it by construction.
- CRCL is **not** special-cased anywhere in this bridge. It appears only
  as an ordinary row wherever it naturally occurs (holdings, daily-bars
  sample symbol in the smoke report, a recommendation/paper-trade/review
  if one exists) — no gateway command, desktop-page section, or contract
  rule treats CRCL differently from any other symbol.

## Allowed gateway commands

```
status                    full status snapshot (coverage, latest reports,
                           holdings, recommendations, paper trading,
                           review, data gaps, next operational action)
holdings                  holdings summary from config/holdings.yaml
recommendations           recommendations summary from data/records/recommendations.jsonl
paper-summary             paper trading summary from data/records/paper_trades.jsonl
review-summary            review summary from data/records/reviews.jsonl
provider-report           latest scripts/check_provider_router.py report (config/wiring only)
provider-router-report    latest scripts/validate_provider_router_live.py report
market-snapshot-smoke     latest scripts/run_market_snapshot_smoke.py report (read-only —
                           never triggers a new run)
data-gaps                 current data gaps from data/records/data_gaps.jsonl
desktop-page              regenerates data/desktop/aegis_status.html + .json
summary                   condensed top-line status
```

Every command returns JSON on stdout: `{"ok": true, "command": ..., "data": ...}`
on success, exit code `0`. A missing source file/record is reported as
an honest `{"status": "no_data", ...}` sub-object — never a crash, never
a fabricated value.

## Forbidden commands

```
buy, sell, trade, order, broker, auto-trade, rebalance,
paper-buy, paper-sell, create-paper-trade,
modify-decision, modify-recommendation
```

Any of these (matched case-insensitively) returns a structured refusal
and exit code `1`:

```json
{
  "ok": false,
  "error": "forbidden_command",
  "command": "buy",
  "message": "'buy' is not a supported command. scripts/aegis_agent_gateway.py (P1C) is a strictly read-only query interface: it never creates PaperTrade records, never calls a broker, never executes a real or simulated trade, and never modifies a Decision/Recommendation record. See docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md."
}
```

An unrecognized command that is neither allowed nor explicitly forbidden
also fails closed — `{"error": "unknown_command", ...}`, exit code `1` —
rather than being silently accepted.

## Desktop status page

`data/desktop/aegis_status.html` (built by
`scripts/build_desktop_status.py`, or regenerated via the gateway's
`desktop-page` command) is the human-facing read-only view of the same
data the gateway exposes. It never fetches live data itself, never shows
fabricated P&L/recommendations/market status, and never modifies
`dashboard/index.html` (a completely separate, untouched file/pipeline).
An optional local-only viewer, `scripts/serve_desktop.py`, serves this
directory on `127.0.0.1:8765` with directory listing disabled.

## What this round explicitly does not implement

Per the task's strict non-goals: no H/US universe, no H/US
`stock_basic`, no sector/fundamentals, no `UniverseBuilder`/Signal
Library/Expert Agents/Decision Engine/Recommendation logic changes, no
`dashboard/index.html` modification, no real trading, no broker
connection, no PaperTrade creation from the gateway/Feishu/user chat, no
composite/weighted scoring, no `.env`/token access, no CRCL
special-casing. The actual OpenClaw skill wiring and Feishu bot
implementation themselves are future work that would consume this
contract, not part of this round's deliverable.

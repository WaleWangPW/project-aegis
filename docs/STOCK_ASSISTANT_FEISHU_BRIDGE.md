# Project Aegis — OpenClaw Stock Assistant Feishu Bridge

## Purpose

Future Feishu delivery for Aegis stock selection must be owned by the
OpenClaw stock assistant, not by the AI-news assistant.

The bridge has two directions:

- Outbound: Aegis creates structured interactive cards; OpenClaw stock
  assistant sends them through its `push.py`.
- Inbound: Feishu card button values are passed back to Aegis and recorded as
  feedback evidence.

## Non Goals

- No real trading.
- No broker API.
- No order placement.
- No trading webhook.
- No position sizing.
- No mutation of `RecommendationRecord`, `PaperTrade`, holdings, review, or
  memory records directly from a button click.

## Files

- `scripts/build_aegis_stock_feishu_cards.py`
  - Reads `data/reports/stock_selection_workbench_latest.json`.
  - Writes `data/reports/aegis_stock_assistant_feishu_cards_latest.json`.
  - Does not read secrets and does not send.

- `scripts/send_aegis_stock_feishu_cards_via_stock_assistant.py`
  - Imports `/Users/weihongwang/shared-vault-workflow/stock-picker/push.py`.
  - Requires `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, and `FEISHU_CHAT_ID`.
  - If credentials are missing or `--dry-run` is used, writes a dry-run report
    and sends nothing.

- `scripts/handle_aegis_stock_card_action.py`
  - Accepts Feishu card `value` JSON.
  - Appends evidence-only records to
    `data/records/aegis_stock_feedback_events.jsonl`.
  - Writes latest status to `data/reports/aegis_stock_feedback_latest.json`.

- `scripts/ingest_dashboard_local_intents.py`
  - Accepts Dashboard-exported `aegis_dashboard_local_intents` JSON.
  - Reuses the same feedback handler.
  - Marks source as `dashboard_local_intent_export`.

- `scripts/run_aegis_dashboard_intent_bridge_server.py`
  - Serves the Dashboard on localhost.
  - Adds `POST /api/dashboard-intents` for browser button clicks.
  - Keeps the same simulation-only/no-broker/no-order safety boundary.

## Button Actions

All button values include:

- `system=project_aegis`
- `source=openclaw_stock_assistant`
- `record_mode=feedback_evidence_only`
- `real_trade_allowed=false`
- `symbol`
- `name`
- `market`
- `status`
- `score`

Supported actions:

| Action | Meaning | Aegis effect |
|---|---|---|
| `aegis_watch` | User wants to add this candidate to simulation watch | append feedback evidence only |
| `aegis_ignore` | User does not want to follow this candidate | append feedback evidence only |
| `aegis_more_news` | User wants more company news | append feedback evidence only |
| `aegis_manual_external` | User indicates possible external manual action | append evidence only; still no trade mutation |

## OpenClaw Stock Assistant Wiring

When the stock assistant receives a card action, it should call:

```bash
python3 /path/to/project-aegis/repo/scripts/handle_aegis_stock_card_action.py '<value-json>'
```

The handler returns a compact status line and writes the durable evidence.

## Dashboard Local Bridge

For daily local use, prefer:

```bash
make serve-dashboard-intent-bridge
```

Then open:

```text
http://localhost:8080/dashboard/index.html
```

When the local bridge is running, Dashboard candidate buttons automatically post
to `/api/dashboard-intents` and write backend feedback evidence. If the bridge
is not running, the page falls back to browser-local receipts and the
`复制后台JSON` button.

## Safety

Button clicks are user feedback, not trading instructions. A later review
stage may consume feedback evidence, but must still pass Aegis gates before
creating any simulation records.

_Source: Codex 2026-07-12_

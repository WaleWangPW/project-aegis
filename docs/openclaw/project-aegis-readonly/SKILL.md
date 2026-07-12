# Project Aegis — Read-Only OpenClaw Skill Scaffold

Produced per `Claude_Cowork_P1C2_OPENCLAW_FEISHU_READONLY_CONNECT.md`.
This is a **documentation scaffold**, not a registered/running OpenClaw
skill — no OpenClaw skill manifest, message-routing config, or Feishu
bot process is created or started by this round. It describes exactly
what a future OpenClaw skill (or any other chat-bot integration) must
do if it wants to query Project Aegis: call the existing read-only
adapter/gateway as a local subprocess, nothing else.

If this repository later adopts a formal OpenClaw skills convention
(e.g. an `openclaw/skills/` directory recognized by a local OpenClaw
installation), this file's content should be copied there verbatim as
`openclaw/skills/project-aegis-readonly/SKILL.md` — the command
contract does not change based on where the file lives.

## What this skill is allowed to do

Read-only queries against already-persisted Project Aegis records and
reports. Nothing else. It has no write capability of any kind.

## The one command shape

Every invocation takes the exact form:

```bash
python scripts/openclaw_aegis_readonly.py "aegis <command>"
```

run from the repository root (`workstations/stock-trading/projects/project-aegis/repo`
in this Vault). This is the **only** shell command an OpenClaw skill or
Feishu bot should ever execute for Project Aegis. It may equivalently
call `scripts/aegis_agent_gateway.py <command>` directly (the adapter is
a thin, logic-free wrapper around it — see
`docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md`), but every example below
uses the adapter form since that's what a chat message naturally maps
to (`"aegis status"` -> the text a user typed, minus nothing).

## Command examples

| User types in Feishu/OpenClaw | Shell command | Returns |
|---|---|---|
| `aegis status` | `python scripts/openclaw_aegis_readonly.py "aegis status"` | Full status snapshot: coverage, latest reports, holdings, recommendations, paper trading, review, data gaps, next action |
| `aegis holdings` | `python scripts/openclaw_aegis_readonly.py "aegis holdings"` | Holdings summary from `config/holdings.yaml` |
| `aegis summary` | `python scripts/openclaw_aegis_readonly.py "aegis summary"` | Condensed top-line status |
| `aegis desktop-page` | `python scripts/openclaw_aegis_readonly.py "aegis desktop-page"` | Regenerates `data/desktop/aegis_status.html`; returns `{"ok": true, "path": ..., "absolute_path": ..., "open_command": ...}` |
| `aegis provider-router-report` | `python scripts/openclaw_aegis_readonly.py "aegis provider-router-report"` | Latest `scripts/validate_provider_router_live.py` report |
| `aegis market-snapshot-smoke` | `python scripts/openclaw_aegis_readonly.py "aegis market-snapshot-smoke"` | Latest `scripts/run_market_snapshot_smoke.py` report (read-only, never triggers a new run) |
| `aegis data-gaps` | `python scripts/openclaw_aegis_readonly.py "aegis data-gaps"` | Current vs. historical/superseded data gaps |

Command text is matched case-insensitively and tolerates extra
whitespace (`"AEGIS STATUS"`, `"  aegis   holdings  "` both work).

## Expected JSON output

Every allowed command except `desktop-page` returns:

```json
{"ok": true, "command": "status", "data": { ... }}
```

`desktop-page` returns a flat shape instead (no `"command"`/`"data"`
wrapper), so a chat bot can hand the user a ready-to-run open command
directly:

```json
{
  "ok": true,
  "path": "data/desktop/aegis_status.html",
  "absolute_path": "/abs/path/.../data/desktop/aegis_status.html",
  "open_command": "open data/desktop/aegis_status.html"
}
```

## Strict forbidden commands

The following are matched case-insensitively and refused by
`scripts/aegis_agent_gateway.py` itself — the adapter has no allow/forbid
logic of its own and cannot bypass this:

```text
buy, sell, trade, order, broker, auto-trade, rebalance,
paper-buy, paper-sell, create-paper-trade,
modify-decision, modify-recommendation
```

## Refusal behavior

```bash
$ python scripts/openclaw_aegis_readonly.py "aegis buy"
```

```json
{
  "ok": false,
  "error": "forbidden_command",
  "command": "buy",
  "message": "'buy' is not a supported command. scripts/aegis_agent_gateway.py (P1C) is a strictly read-only query interface: ..."
}
```

Exit code `1`. An OpenClaw skill/Feishu bot must surface this refusal
message to the user verbatim (or a faithful translation) rather than
silently dropping the request, retrying it as something else, or
inventing its own success response.

An unrecognized command (not in the allowed set, not in the forbidden
set) is also refused, with `{"ok": false, "error": "unknown_command",
...}`, exit 1 — never silently accepted or guessed at.

A malformed input that doesn't match the `"aegis <command>"` shape at
all (e.g. a bare `"hello"` with no `"aegis "` prefix) is refused by the
adapter itself before it ever reaches the gateway: `{"ok": false,
"error": "invalid_command_text", ...}`, exit 1.

## What this scaffold does not do

- It does not install, register, or run an OpenClaw skill.
- It does not connect to Feishu, and stores no Feishu App ID/App
  Secret/open_id/chat_id anywhere in this repository.
- It does not read, print, or expose `.env` or any token (see
  `docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md`'s "Never read `.env`"
  section — unchanged this round).
- It does not create a `PaperTrade`, call a broker, or execute any
  trade, real or simulated.
- It does not special-case `CRCL` — it only ever appears as whatever
  row already exists in `config/holdings.yaml`.

See `docs/P1C2_OPENCLAW_FEISHU_SETUP_RUNBOOK.md` for the operational
steps to actually wire a Feishu bot to this command shape, and
`scripts/check_openclaw_aegis_readonly.py` for a local, credential-free
script that verifies the command contract above still holds.

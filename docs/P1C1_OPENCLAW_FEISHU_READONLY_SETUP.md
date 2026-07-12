# Project Aegis — P1C.1 OpenClaw/Feishu Read-Only Setup

Produced per `Claude_Cowork_P1C1_DESKTOP_POLISH_OPENCLAW_FEISHU_PREP.md`,
Step 3. This document describes how to wire an OpenClaw skill or Feishu
bot to Project Aegis **read-only**. It does not connect to Feishu itself
— no credentials, no secrets, no network call to any chat platform are
introduced by this round. It only prepares the local, read-only surface
such a channel would call.

## The single entry point

Every OpenClaw/Feishu integration must call only:

```text
scripts/aegis_agent_gateway.py
```

or the thin text-command adapter built this round:

```text
scripts/openclaw_aegis_readonly.py
```

`scripts/openclaw_aegis_readonly.py` exists purely to translate a raw
chat-message string like `"aegis status"` into a gateway command — it
has **no allow/forbid logic of its own**. Every command, allowed or
refused, is decided by `scripts.aegis_agent_gateway.dispatch()` alone.
An OpenClaw skill or Feishu bot may call either script; neither grants
any capability the other doesn't already have.

## Allowed command mapping

A Feishu/OpenClaw user typing one of these phrases should map to the
corresponding gateway command:

| Feishu/OpenClaw text | Gateway command | What it returns |
|---|---|---|
| `aegis status` | `status` | Full status snapshot (coverage, latest reports, holdings, recommendations, paper trading, review, data gaps, next action) |
| `aegis holdings` | `holdings` | Holdings summary from `config/holdings.yaml` |
| `aegis summary` | `summary` | Condensed top-line status |
| `aegis desktop-page` | `desktop-page` | Regenerates `data/desktop/aegis_status.html` and returns `{"ok": true, "path": ..., "absolute_path": ..., "open_command": ...}` |
| `aegis provider-router-report` | `provider-router-report` | Latest `scripts/validate_provider_router_live.py` report |
| `aegis market-snapshot-smoke` | `market-snapshot-smoke` | Latest `scripts/run_market_snapshot_smoke.py` report (read-only — never triggers a new run) |
| `aegis data-gaps` | `data-gaps` | Current vs. historical/superseded data gaps |

Every response is JSON: `{"ok": true, "command": ..., "data": ...}` (the
`desktop-page` command instead returns the flat
`{"ok": true, "path": ..., "absolute_path": ..., "open_command": ...}`
shape shown above, so a chat bot can hand the user a ready-to-run open
command without unwrapping anything).

## Forbidden command behavior

`buy`, `sell`, `trade`, `order`, `broker`, `auto-trade`, `rebalance`,
`paper-buy`, `paper-sell`, `create-paper-trade`, `modify-decision`,
`modify-recommendation` (matched case-insensitively) are refused by the
gateway itself — the adapter cannot bypass this. Refusal shape:

```json
{
  "ok": false,
  "error": "forbidden_command",
  "command": "buy",
  "message": "'buy' is not a supported command. scripts/aegis_agent_gateway.py (P1C) is a strictly read-only query interface: ..."
}
```

Exit code `1`. An OpenClaw skill/Feishu bot must surface this refusal
message to the user verbatim (or a translated equivalent) rather than
silently dropping the request or retrying it as something else.

## Pairing / allowlist guidance

Until a real OpenClaw/Feishu bridge is implemented (out of scope for
this round — see "What this round does not implement" below), any
future integration should:

- run `scripts/aegis_agent_gateway.py`/`scripts/openclaw_aegis_readonly.py`
  as a local subprocess only — never expose it as an open network
  endpoint;
- restrict which Feishu user IDs/OpenClaw channels are allowed to invoke
  it at all (an allowlist maintained outside this repository — this
  repository has no user/auth model of its own);
- treat every response as **read-only information to display**, never
  as an instruction to take a further automated action (e.g. a bot must
  not interpret a `data_gap` count as license to auto-retry a live run);
- if a future round adds real Feishu API credentials, those credentials
  must live in the Feishu-side bot configuration, never in this
  repository, and never read by any script here — `scripts/
  aegis_agent_gateway.py` and `scripts/openclaw_aegis_readonly.py` both
  remain credential-free by construction (neither imports a provider
  adapter or touches `os.environ`/`.env`/`dotenv`).

## Never read `.env`

Neither `scripts/aegis_agent_gateway.py` nor
`scripts/openclaw_aegis_readonly.py` imports a provider adapter,
`os.environ`, or `dotenv` at all — there is no code path in either
script that could read `TUSHARE_TOKEN` or any other token, let alone
print one. Confirmed by source-pattern tests (no bare-substring checks —
see `tests/test_openclaw_aegis_readonly.py`).

## Never create PaperTrade

Neither script imports `PaperTrade`/`PaperTradeRepository.append`, and
`create-paper-trade`/`paper-buy`/`paper-sell` are explicit forbidden
commands, refused before any handler code runs.

## Never call broker APIs

No broker integration exists anywhere in Project Aegis (Master Spec
ADR-004). `broker`/`auto-trade`/`trade`/`order`/`buy`/`sell`/`rebalance`
are all explicitly forbidden gateway commands regardless.

## CRCL is not special-cased

CRCL only ever appears as whatever already-persisted data happens to
contain it (currently: the one real holding in `config/holdings.yaml`).
Neither `scripts/aegis_agent_gateway.py` nor
`scripts/openclaw_aegis_readonly.py` contains any conditional logic
keyed on the literal string `"CRCL"`.

## What this round does not implement

The actual Feishu bot process, its message-routing configuration, and
any OpenClaw skill manifest that would call
`scripts/openclaw_aegis_readonly.py` in production are **not** built
this round — this document only describes the contract such an
integration must follow once it exists, and this round only ships the
local, credential-free adapter it would call. No H/US universe, no
Decision/Expert Agent changes, no `dashboard/index.html` modification,
no real trading, no broker connection, no composite scoring.

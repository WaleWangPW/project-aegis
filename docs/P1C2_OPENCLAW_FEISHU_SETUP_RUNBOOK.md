# Project Aegis — P1C.2 OpenClaw/Feishu Setup Runbook

Produced per `Claude_Cowork_P1C2_OPENCLAW_FEISHU_READONLY_CONNECT.md`.
This runbook is the operational companion to
`docs/openclaw/project-aegis-readonly/SKILL.md` (the command contract)
and `docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md` (the original P1C.1
read-only contract, still authoritative). It walks through connecting a
local OpenClaw instance's Feishu channel to Project Aegis, read-only,
without ever putting a secret in this repository.

**This document contains no real App ID, App Secret, `open_id`,
`chat_id`, user ID, or any other Feishu/OpenClaw identifier.** Every
value below is a placeholder in angle brackets or a generic example.
Fill in real values only in your local OpenClaw configuration, never in
this repo, never in a commit, never in a Cowork session transcript.

## 1. Prerequisite check

Run these locally (not from inside this Cowork sandbox — `openclaw` is
not installed here; see "Environment status" below):

```bash
openclaw --version
openclaw channels login --channel feishu
openclaw gateway restart
```

- `openclaw --version` confirms OpenClaw itself is installed and on a
  version that supports the Feishu channel.
- `openclaw channels login --channel feishu` starts (or refreshes) the
  Feishu channel's own credential flow. This is where your Feishu App
  ID/App Secret get entered — **into OpenClaw's own credential store,
  never into this repository**. If you've already logged in once,
  re-running this is how you rotate or refresh the session.
- `openclaw gateway restart` picks up any channel/config change made by
  the previous two commands.

If any of these three commands fail, do not proceed to step 4 (test
messages) — fix the OpenClaw/Feishu connection itself first. None of
that troubleshooting touches Project Aegis.

## 2. Suggested Feishu access control

Project Aegis's own gateway (`scripts/aegis_agent_gateway.py`) has no
user/auth model — it will answer whatever process invokes it. All
access control must happen at the OpenClaw/Feishu layer, before a
message ever reaches `scripts/openclaw_aegis_readonly.py`:

- **DM allowlist or pairing, not an open public DM.** Configure OpenClaw
  so only your own Feishu user ID (or a small, explicitly-approved list)
  can trigger the Project Aegis skill/command in a direct message.
  Consult your OpenClaw version's own docs for the exact allowlist/
  pairing mechanism (e.g. a `bindings`/`allowed_users` style config) —
  this runbook intentionally does not prescribe a specific config key
  name, since that's OpenClaw-version-specific and this repo has no
  say over it.
- **Group allowlist if group chat is used.** If you want this skill
  reachable from a Feishu group rather than only DM, restrict it to a
  specific, explicitly-approved group ID (again configured on the
  OpenClaw/Feishu side, not in this repo).
- **Mention required in groups, unless you explicitly disable it.** In
  a group chat, prefer requiring an `@mention` of the bot before it
  responds — this avoids the bot reacting to every message containing
  the word "aegis". Only disable this if you've deliberately decided a
  dedicated group is safe for un-mentioned trigger phrases.
- Treat every response as **read-only information to display**, never
  as license for the bot to take a further automated action (e.g. a
  `data-gaps` count is not permission to auto-retry a live smoke run).

## 3. Test messages

Once the Feishu channel is live and paired/allowlisted, send these
messages to the bot (in the allowlisted DM or group) and confirm the
responses match `docs/openclaw/project-aegis-readonly/SKILL.md`'s
command table:

| Message | Expected |
|---|---|
| `aegis status` | `{"ok": true, "command": "status", "data": {...}}` |
| `aegis holdings` | `{"ok": true, "command": "holdings", "data": {...}}` — shows the real `CRCL` holding from `config/holdings.yaml` if present |
| `aegis summary` | `{"ok": true, "command": "summary", "data": {...}}` — condensed top-line view |
| `aegis desktop-page` | `{"ok": true, "path": ..., "absolute_path": ..., "open_command": ...}` |
| `aegis buy` | **Must be refused**: `{"ok": false, "error": "forbidden_command", "command": "buy", "message": "..."}`, non-zero exit surfaced back through the channel |

If the bot returns anything other than the refusal shape for `aegis
buy` (e.g. it silently ignores the message, or worse, executes
something), stop and treat that as a configuration bug in the
OpenClaw-side message routing — the gateway itself is proven (by
`tests/test_aegis_agent_gateway.py` and
`scripts/check_openclaw_aegis_readonly.py`) to always refuse it; a
different result means something upstream of the gateway is not calling
it correctly.

## 4. No secrets in repo

- Never commit a Feishu App ID/App Secret, a Tushare token, `.env`
  contents, or any OpenClaw session/credential file into this
  repository — not even into `docs/`, not even redacted-looking
  examples that are actually real.
- `scripts/aegis_agent_gateway.py`, `scripts/openclaw_aegis_readonly.py`,
  `scripts/check_openclaw_aegis_readonly.py`, and this runbook are all
  confirmed (by source-pattern tests) to never import `os.environ`,
  `dotenv`, or any provider adapter — there is no code path anywhere in
  this integration that could read a token even by accident.
- If you ever paste a real Feishu App Secret or Tushare token into a
  chat with an AI assistant (including this one) while working on this
  repo, treat that secret as compromised and rotate it — do not rely on
  the assistant to have "not seen" it.

## 5. How to update or rotate the Feishu secret (outside this repo)

1. Rotate the App Secret in the Feishu Open Platform console for your
   app (this is entirely on Feishu's side, unrelated to this repo).
2. Update the credential in OpenClaw's own config/credential store —
   typically via `openclaw channels login --channel feishu` again, or
   your OpenClaw version's dedicated credential-update command.
3. Run `openclaw gateway restart` to pick up the new credential.
4. Re-run the test messages in section 3 to confirm the channel still
   works after rotation.

None of these steps touch this repository at any point.

## 6. Reading OpenClaw logs for troubleshooting

- Check OpenClaw's own log location for your installation (commonly
  under its config/data directory — consult `openclaw --version`'s
  output or your OpenClaw install docs for the exact path on your
  machine, since this varies by install method and version).
- Look for the exact shell command OpenClaw executed for a given
  message — it should be exactly
  `python scripts/openclaw_aegis_readonly.py "aegis <command>"` (or the
  wrapper `scripts/aegis_openclaw_command.sh aegis <command>`), run
  from this repo's root. If the logged command differs from this
  shape, that's the bug to fix on the OpenClaw-side routing config, not
  in Project Aegis.
- You can always reproduce exactly what OpenClaw should be doing,
  entirely locally and without any Feishu credential, via:
  ```bash
  python scripts/check_openclaw_aegis_readonly.py
  ```
  This exercises the same adapter the same way OpenClaw would (a
  subprocess call with one `"aegis <command>"` string) and prints a
  JSON pass/fail summary — a good first troubleshooting step before
  assuming the problem is on the Feishu/OpenClaw side.

## Environment status (this round)

`openclaw` is **not installed** in this Cowork sandbox
(`which openclaw` / `openclaw --version` both fail with "command not
found"). This is expected — this sandbox has no Feishu/OpenClaw
runtime, no outbound network to Feishu's API, and per this task's own
non-goals, no attempt was made to install or configure one. Everything
in this runbook was written from the existing, already-verified
read-only contract (`docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md`) and
from `scripts/check_openclaw_aegis_readonly.py`'s local, credential-free
verification (see `docs/P1C2_OPENCLAW_FEISHU_READONLY_CONNECT_RESULT.md`
for the exact commands run and their output). Steps 1-3 above are meant
to be followed **manually, on the user's own machine, where `openclaw`
and a real Feishu app already exist** — this round could not and did
not attempt to run them.

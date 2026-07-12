# Project Aegis — P1C.2 OpenClaw/Feishu Read-Only Connect — Result

Per `Claude_Cowork_P1C2_OPENCLAW_FEISHU_READONLY_CONNECT.md`. Builds on
P1C (`docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md`) and P1C.1
(`docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md`) — this round prepares
the scaffolding, runbook, and local verification tooling to actually
connect a real OpenClaw/Feishu channel to Project Aegis's existing
read-only surface. It does **not** stand up a real Feishu bot process
or install/configure OpenClaw itself (neither is available in this
Cowork sandbox, and neither was required by the task).

## What was implemented

### 1. OpenClaw skill scaffold

`docs/openclaw/project-aegis-readonly/SKILL.md` — a documentation
scaffold (not a registered/running OpenClaw skill) describing:

- the one command shape an integration should ever use:
  `python scripts/openclaw_aegis_readonly.py "aegis <command>"`;
- a full command-example table (`aegis status`/`holdings`/`summary`/
  `desktop-page`/`provider-router-report`/`market-snapshot-smoke`/
  `data-gaps`) mapped to the exact shell command and what it returns;
- the exact JSON success shape (`{"ok": true, "command": ..., "data":
  ...}`, with `desktop-page`'s flat exception documented separately);
- the strict forbidden-command list (unchanged from P1C/P1C.1: `buy`,
  `sell`, `trade`, `order`, `broker`, `auto-trade`, `rebalance`,
  `paper-buy`, `paper-sell`, `create-paper-trade`, `modify-decision`,
  `modify-recommendation`);
- refusal behavior (structured JSON, exit 1) and unknown-command/
  malformed-input behavior;
- an explicit "what this scaffold does not do" section (no OpenClaw
  skill registration, no Feishu connection, no secrets, no PaperTrade,
  no broker, no CRCL special-casing).

If this repo later adopts a formal `openclaw/skills/` convention
recognized by a local OpenClaw install, the file notes it should be
copied there verbatim — the command contract itself doesn't change
based on where the file lives.

### 2. Feishu/OpenClaw setup runbook

`docs/P1C2_OPENCLAW_FEISHU_SETUP_RUNBOOK.md` covers, in order:

1. Prerequisite check (`openclaw --version`, `openclaw channels login
   --channel feishu`, `openclaw gateway restart`) — to be run by the
   user on their own machine, not from this sandbox.
2. Suggested Feishu access control: DM allowlist/pairing (not an open
   public DM), group allowlist if group chat is used, `@mention`
   required in groups unless explicitly disabled, and "every response
   is read-only information to display, never license for further
   automated action."
3. Test messages (`aegis status`/`holdings`/`summary`/`desktop-page`,
   and `aegis buy` which must be refused) with expected responses.
4. No secrets in repo — explicit statement of what must never be
   committed, and confirmation that every script in this integration
   is structurally incapable of reading one.
5. How to rotate the Feishu secret entirely outside this repo (Feishu
   console → OpenClaw credential store → `openclaw gateway restart` →
   re-test).
6. How to read OpenClaw's own logs for troubleshooting, and how to
   reproduce the same check locally without any Feishu credential via
   `scripts/check_openclaw_aegis_readonly.py`.

**No real App ID, App Secret, `open_id`, `chat_id`, or user ID appears
anywhere in this document** — every value is a placeholder or a
structural description of where a real value would go (in OpenClaw's
own config, never in this repo). Confirmed by a dedicated test scanning
for secret-shaped strings (see Tests below), not just a bare substring
check on the word "secret."

### 3. Local verification script

`scripts/check_openclaw_aegis_readonly.py` — requires no Feishu
credentials, no `openclaw` install, no network. Shells out to
`scripts/openclaw_aegis_readonly.py` exactly the way a real OpenClaw/
Feishu channel would (one subprocess call per `"aegis <command>"`
string) and checks:

- `aegis status`/`aegis holdings`/`aegis summary` each return `{"ok":
  true, ...}` and exit 0;
- `aegis buy` is refused (`{"ok": false, "error": "forbidden_command",
  ...}`, non-zero exit);
- the forbidden-command call never creates or modifies
  `data/records/paper_trades.jsonl` — proven by snapshotting the
  file's `(mtime, sha256)` fingerprint immediately before and after the
  call, not just trusting the JSON response;
- `dashboard/index.html` is byte-identical to the Vault-level copy,
  using the same check every other P1B/P1C test file already uses —
  skipped honestly (never silently reported as pass) if the Vault-level
  copy isn't present in the running environment.

Prints a single JSON summary to stdout (`{"ok": <bool>, "checks":
{...}}`) and exits 0/1 accordingly. The script itself never imports a
provider adapter, `os.environ`, or `dotenv`, and never opens any file
for writing (confirmed by source-pattern tests).

### 4. Optional command wrapper

`scripts/aegis_openclaw_command.sh` — a tiny bash wrapper that runs
`python3 scripts/openclaw_aegis_readonly.py "$*"`. No logic, no
secrets, no write operations; exit code and stdout pass straight
through from the adapter. Verified locally:
`./scripts/aegis_openclaw_command.sh aegis status` and `aegis buy`
behave identically to calling the Python script directly.

## Strict non-goals (confirmed unchanged this round)

No H/US universe. No H/US `stock_basic`. No Decision Engine/Expert
Agents/Recommendation logic change. `dashboard/index.html` byte-identical
(confirmed by `test_dashboard_index_html_unchanged`, now present in
four test files). No broker connection, no real trading. No PaperTrade
created from Feishu/OpenClaw/user chat (confirmed: no script this round
contains `PaperTrade(`, and the local verification script proves the
forbidden command's file-level side effects are nil). No composite
scoring (confirmed: `composite_score` does not appear in any new
script). No `.env`/token read, printed, grepped, or catted anywhere
this round (confirmed: no new script imports `os.environ`/`dotenv`/any
provider adapter). No Feishu App Secret or Tushare token stored in this
repository (confirmed: no real-looking secret pattern found in either
new doc, by a dedicated regex-based test — not just a bare-word
"secret" check). CRCL not special-cased (confirmed: no new script
contains a conditional keyed on the literal string `"CRCL"`; it appears
only as the one real holding row `scripts/openclaw_aegis_readonly.py
"aegis holdings"` returns).

## Tests

**12 required test items**, all satisfied (new file
`tests/test_check_openclaw_aegis_readonly.py`, 19 tests):

1. OpenClaw adapter allowed command works — already covered by
   `tests/test_openclaw_aegis_readonly.py::test_run_command_maps_allowed_command_to_gateway_result`
   (P1C.1, re-verified unchanged this round).
2. OpenClaw adapter forbidden command is refused — already covered by
   `tests/test_openclaw_aegis_readonly.py::test_run_command_still_refuses_forbidden_commands`
   (P1C.1, re-verified unchanged).
3. Check script returns success when allowed commands pass and
   forbidden command fails as expected —
   `test_check_script_reports_ok_true_against_the_real_repo`,
   `test_check_script_cli_prints_json_and_exits_zero`.
4. Check script does not read `.env` —
   `test_check_script_never_touches_dotenv_or_token`.
5. Check script does not create/modify PaperTrade —
   `test_forbidden_command_check_fails_if_paper_trades_file_changes`
   (proves the check actually *fails* if the file were to change, not
   just that it happens to pass today),
   `test_forbidden_command_check_passes_when_file_absent_both_times`,
   `test_check_script_never_constructs_a_paper_trade_or_broker_call`.
6. Feishu setup docs contain allowlist/pairing guidance —
   `test_runbook_exists_and_has_allowlist_pairing_guidance`.
7. Feishu setup docs do not contain placeholder-looking real secrets —
   `test_docs_contain_no_placeholder_looking_real_secrets` (parametrized
   over both new docs, regex-based, not a bare substring check).
8. OpenClaw skill/runbook commands point to read-only adapter —
   `test_skill_scaffold_exists_and_points_to_readonly_adapter`.
9. `dashboard/index.html` unchanged —
   `test_dashboard_check_matches_real_repo_dashboard`,
   `test_dashboard_index_html_unchanged`.
10. No broker/real trading code —
    `test_check_script_never_constructs_a_paper_trade_or_broker_call`.
11. No composite scoring — `test_check_script_never_uses_composite_scoring`.
12. CRCL not special-cased — `test_check_script_does_not_special_case_crcl`.

Plus supporting tests: `_run_adapter`/fake-injection tests proving the
checker fails closed when an allowed command's response isn't actually
`ok: true`; a dashboard-check honest-skip test when the Vault-level
copy is absent; a wrapper-script secret/write-operation scan.

**pytest -v: 466 passed, 0 failed** (447 before this round + 19 new, all
in the new `tests/test_check_openclaw_aegis_readonly.py`).

## Commands run

```text
$ pytest -v
============================== 466 passed in ~7s ==============================

$ python scripts/check_openclaw_aegis_readonly.py
{
  "ok": true,
  "checks": {
    "status": {"command": "aegis status", "passed": true, "exit_code": 0, "response_ok": true},
    "holdings": {"command": "aegis holdings", "passed": true, "exit_code": 0, "response_ok": true},
    "summary": {"command": "aegis summary", "passed": true, "exit_code": 0, "response_ok": true},
    "buy_refused_no_paper_trade_write": {
      "command": "aegis buy", "passed": true, "exit_code": 1,
      "response_ok": false, "response_error": "forbidden_command",
      "paper_trades_file_untouched": true
    },
    "dashboard_unchanged": {"passed": true, "status": "compared", "byte_identical": true}
  }
}

$ python scripts/openclaw_aegis_readonly.py "aegis status"    → exit 0, ok: true
$ python scripts/openclaw_aegis_readonly.py "aegis holdings"  → exit 0, ok: true, shows the real CRCL holding
$ python scripts/openclaw_aegis_readonly.py "aegis summary"   → exit 0, ok: true
$ python scripts/openclaw_aegis_readonly.py "aegis buy"       → exit 1, {"ok": false, "error": "forbidden_command", ...}
```

`openclaw` is **not installed** in this Cowork sandbox:

```text
$ openclaw --version
bash: openclaw: command not found (exit 127)

$ openclaw gateway status
bash: openclaw: command not found (exit 127)
```

This is expected and does not fail this round's tests — per the task's
explicit instruction, OpenClaw's absence is documented, not worked
around or faked. `docs/P1C2_OPENCLAW_FEISHU_SETUP_RUNBOOK.md`'s
"Environment status" section states this plainly and directs the
prerequisite steps to be run by the user on their own machine.

## Real local data referenced (read-only, never modified)

- `config/holdings.yaml` — 1 real holding (CRCL), unchanged.
- `data/records/data_gaps.jsonl` — 28 rows, untouched (fingerprint
  proven unchanged across the `aegis buy` verification call).
- `data/processed/provider_diagnostics/provider_coverage_report.json`,
  `data/processed/provider_router/provider_router_live_report.json`,
  `data/processed/market_snapshot_smoke/market_snapshot_smoke_report.json`
  — all read only, none run/overwritten this round.

## Verification against strict non-goals

- No H/US universe/`stock_basic`/sector/fundamentals implemented.
- Decision Engine, Expert Agents, Recommendation logic: untouched.
- `dashboard/index.html`: byte-identical (test-confirmed in four test
  files, and by `scripts/check_openclaw_aegis_readonly.py` itself).
- No broker connection, no real trading, no PaperTrade creation from
  chat/bridge/gateway/adapter/wrapper — and now also *provably* no
  file-level side effect from a forbidden command, not just an honest
  JSON refusal.
- No composite/weighted scoring anywhere in the new scripts/docs.
- No `.env`/token read, print, grep, or cat anywhere this round.
- No Feishu App Secret or Tushare token stored in this repository.
- CRCL not special-cased — appears only as the one real holding row.

## Next step

Suggested, non-scope-expanding next actions (none require further
approval to attempt, but any new scope does):
1. On the user's own machine (where `openclaw` and a real Feishu app
   already exist), follow `docs/P1C2_OPENCLAW_FEISHU_SETUP_RUNBOOK.md`
   sections 1-3: run the three prerequisite commands, configure DM/
   group allowlisting, then send the test messages and confirm they
   match the expected responses (especially that `aegis buy` is
   refused through the real channel, not just locally).
2. If the real channel ever behaves differently from
   `scripts/check_openclaw_aegis_readonly.py`'s local result, treat
   that as an OpenClaw-side routing bug — the gateway/adapter's
   behavior is already proven correct by this round's tests.
3. Only with new, explicit approval: any further scope beyond
   read-only querying (e.g. push notifications on new
   recommendations/data gaps) — not requested or implemented this
   round.

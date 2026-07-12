# Project Aegis — P1C.1 Desktop Polish + OpenClaw/Feishu Read-Only Prep — Result

Per `Claude_Cowork_P1C1_DESKTOP_POLISH_OPENCLAW_FEISHU_PREP.md`. Builds
on P1C (`docs/P1C_READONLY_BRIDGE_DESKTOP_VIEW_RESULT.md`,
`docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md`) — this round only polishes
the existing read-only desktop page and prepares (but does not build)
an OpenClaw/Feishu integration.

## User-reported problems (all fixed)

1. **`A` displayed as `一个`, `US` displayed as `我们`.** Browser
   translation tools (Google Translate and similar) auto-translate short,
   ambiguous tokens with no surrounding context. Fixed with a two-layer
   defense in `scripts/build_desktop_status.py::render_html()`:
   document-level `<html lang="zh-CN" translate="no">`, `<meta
   name="google" content="notranslate">`, `<body translate="no"
   class="notranslate">`; and per-element `class="notranslate"
   translate="no"` wrapping on every market code, status badge, run_id,
   timestamp, symbol, and data_type token via new `_market_cell()`/
   `_code()` helpers and an updated `_badge()`.
2. **Market codes not rendered as human labels.** Market codes now
   render as `A股`/`H股`/`美股` (via `_MARKET_LABELS`/`_market_label()`),
   never the bare `A`/`H`/`US` strings a translator could grab onto.
3. **A股 coverage always showed `unknown`.** P1A's real Tushare coverage
   report (`data/processed/provider_diagnostics/provider_coverage_report.json`,
   `run_id: provider_diag_20260704_154328`) already confirms A's
   `daily_bars`/`index_bars`/`stock_basic`/`trading_calendar` checks all
   `pass` — the desktop builder previously never read this file for
   coverage purposes. New `_provider_coverage_summary()` reads only
   `market == "A"` checks, splits them into core
   (`daily_bars`/`index_bars`/`stock_basic`/`trading_calendar`) and
   enhanced (`sector_classification`/`fundamentals`), and
   `_coverage_summary()` now sets `coverage["A"] = "confirmed_tushare"`
   whenever all core checks are `pass`. Enhanced data (still `unknown` in
   the real report) is tracked and shown separately as "增强数据未确认"
   — it never gates the core verdict, per the task's explicit
   instruction. H/US coverage logic is completely unchanged: still
   derived only from `provider_router_live_report.json` +
   `market_snapshot_smoke_report.json`.
4. **Old `yfinance package is not installed` warnings shown as current.**
   A later local `ProviderRouter`-live/`MarketSnapshot`-smoke run already
   confirmed H/US pass, but the desktop page kept showing the old
   dependency-missing gaps as unresolved. New `_split_stale_gaps()`
   reclassifies a gap from "current" to "historical/superseded" only if
   **all three** hold: its `message` matches a known stale marker
   (`"yfinance package is not installed"` / `"yfinance client/package is
   not available"`, case-insensitive), its `market` is *currently*
   confirmed (`confirmed_live`/`confirmed_tushare`), and its own
   `created_at` predates the confirming report's `created_at`.
   `data/records/data_gaps.jsonl` is **never deleted or rewritten** —
   only the *display* splits it into a "current, unresolved" table plus
   a collapsed `<details>`"历史数据缺口 / 已被后续验证覆盖" section.
   Verified against the real local data: 28 total gaps → 4 current
   (fresh "No daily/index bars returned for ..." messages, dated
   2026-07-04) + 24 historical (all old "yfinance package is not
   installed" messages).

## Gateway changes (`scripts/aegis_agent_gateway.py`)

- `desktop-page` now returns a flat, agent-friendly shape:
  ```json
  {
    "ok": true,
    "path": "data/desktop/aegis_status.html",
    "absolute_path": "/abs/path/to/data/desktop/aegis_status.html",
    "open_command": "open data/desktop/aegis_status.html"
  }
  ```
  instead of the previous `{"ok": true, "command": "desktop-page",
  "data": {"html_path": ..., "json_path": ...}}` wrapper. This is a
  **deliberate breaking change** per the task's exact required schema.
  Every other command's shape (`{"ok", "command", "data"}`) is
  unchanged.
- `dispatch()`/`build_status()` gained a new required
  `provider_coverage_report` parameter (CLI: `--provider-coverage-report`,
  default `data/processed/provider_diagnostics/provider_coverage_report.json`),
  threaded through the `status`, `desktop-page`, `summary`, and
  `data-gaps` commands.
- Allowed commands (`status`, `holdings`, `recommendations`,
  `paper-summary`, `review-summary`, `provider-report`,
  `provider-router-report`, `market-snapshot-smoke`, `data-gaps`,
  `desktop-page`, `summary`) and forbidden commands (`buy`, `sell`,
  `trade`, `order`, `broker`, `auto-trade`, `rebalance`, `paper-buy`,
  `paper-sell`, `create-paper-trade`, `modify-decision`,
  `modify-recommendation`) are unchanged and re-verified by
  `test_allowed_commands_set_matches_task_spec`/
  `test_forbidden_commands_set_matches_task_spec`.

## OpenClaw/Feishu read-only prep

- New `scripts/openclaw_aegis_readonly.py` — a pure text-to-gateway-
  command adapter. Parses `"aegis <command>"` (case-insensitive prefix,
  extra whitespace tolerated) and delegates entirely to
  `scripts.aegis_agent_gateway.dispatch()`. It has **no allow/forbid
  logic of its own** — every command, allowed or forbidden, is decided
  solely by the gateway (verified by
  `test_adapter_has_no_allow_or_forbid_logic_of_its_own`, which greps for
  the absence of `ALLOWED_COMMANDS`/`FORBIDDEN_COMMANDS` in the adapter's
  own source). Never reads `.env`/tokens, never creates `PaperTrade`,
  never calls a broker, never special-cases CRCL — all guaranteed by the
  same source-pattern tests used throughout this project.
- New `docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md` — the read-only
  contract: the single entry point (gateway or adapter), the allowed
  command mapping table, the forbidden-command refusal shape, pairing/
  allowlist guidance (subprocess-only, never an open network endpoint,
  credentials live in Feishu-side bot config only, never in this repo),
  and explicit confirmation sections for "never read `.env`", "never
  create PaperTrade", "never call broker APIs", and "CRCL is not
  special-cased." Explicitly states what this round does **not**
  implement: no real Feishu bot process, no OpenClaw skill manifest —
  only the local, credential-free adapter and the contract it must
  follow.

## Strict non-goals (confirmed unchanged this round)

No H/US universe. No H/US `stock_basic`. No sector/fundamentals. No
`UniverseBuilder`/Signal Library/Expert Agents/Decision Engine/
Recommendation logic change. `dashboard/index.html` byte-identical
(confirmed by `test_dashboard_index_html_unchanged` in three separate
test files). No broker connection, no real trading, no PaperTrade
creation from the gateway/adapter/Feishu/user chat (confirmed:
`PaperTrade(` does not appear in either script's source). No composite/
weighted scoring (confirmed: `composite_score` does not appear in the
adapter's source; the gateway/desktop builder never computed one to
begin with). No `.env`/token read/print/grep/cat anywhere (confirmed:
neither script imports `os.environ`, `dotenv`, or any provider adapter
at all). CRCL not special-cased (confirmed: no conditional logic keyed
on the literal string `"CRCL"` in either script).

## Tests

**15 required test items**, all satisfied:

1. Generated desktop HTML has `translate="no"`/notranslate handling —
   `test_desktop_html_has_translate_no_and_notranslate_wrapping`.
2. Market labels render as `A股`/`H股`/`美股` —
   `test_market_labels_render_as_human_chinese`.
3. Status tokens render as human labels, not raw/auto-translatable
   strings — `test_status_tokens_render_as_human_labels_not_raw`.
4. A core coverage is `已验证` when A core checks pass in the provider
   coverage report — `test_a_core_coverage_confirmed_when_provider_coverage_report_passes`
   (plus a negative counterpart,
   `test_a_core_coverage_not_confirmed_when_a_core_check_fails`).
5. H/US coverage is `已验证` when ProviderRouter live + smoke pass,
   unaffected by the new parameter —
   `test_h_us_coverage_still_confirmed_from_provider_router_live_and_smoke`
   (plus the pre-existing
   `test_provider_router_live_and_smoke_reports_are_read_not_recomputed`).
6. Stale yfinance dependency gaps are not shown as current unresolved
   gaps after a later pass —
   `test_stale_yfinance_gap_superseded_by_later_pass_is_not_shown_as_current`.
7. Gateway `desktop-page` returns `path`/`open_command` —
   `test_desktop_page_command_writes_files`,
   `test_cli_main_desktop_page_returns_open_command`, and the
   `test_every_allowed_command_returns_ok_json_and_exit_zero[desktop-page]`
   special case.
8. OpenClaw adapter maps allowed commands to the gateway —
   `test_run_command_maps_allowed_command_to_gateway_result`,
   `test_run_command_maps_desktop_page_to_flat_gateway_shape`.
9. Forbidden commands stay refused —
   `test_run_command_still_refuses_forbidden_commands`,
   `test_run_command_refuses_every_forbidden_command_variant` (both in
   the new adapter test file, plus the existing gateway-level forbidden
   tests, unchanged).
10. `dashboard/index.html` unchanged —
    `test_dashboard_index_html_unchanged` (present in all three test
    files: `test_build_desktop_status.py`, `test_aegis_agent_gateway.py`,
    `test_openclaw_aegis_readonly.py`).
11. No token read/printed —
    `test_build_desktop_status_never_touches_dotenv_or_token`,
    `test_gateway_never_touches_dotenv_or_token_or_broker`,
    `test_adapter_never_touches_dotenv_or_token`.
12. No broker/real trading —
    `test_build_desktop_status_never_creates_paper_trades_or_broker_references`,
    `test_gateway_never_constructs_a_paper_trade_object`,
    `test_adapter_never_constructs_a_paper_trade_or_broker_call`.
13. No manual PaperTrade creation — same tests as #12 (`PaperTrade(`
    absent from every changed/new script's source).
14. No composite scoring — `test_adapter_never_uses_composite_scoring`
    (the gateway/desktop builder never had composite scoring to begin
    with; grepped for completeness).
15. CRCL not special-cased —
    `test_gateway_does_not_special_case_crcl`,
    `test_adapter_does_not_special_case_crcl`.

**pytest -v: 447 passed, 0 failed** (412 before this round + 35 new: 7
in `tests/test_build_desktop_status.py`, 1 in
`tests/test_aegis_agent_gateway.py`, 27 in the new
`tests/test_openclaw_aegis_readonly.py`).

## Commands run

```text
$ pytest -v
============================== 447 passed in ~2s ==============================

$ python scripts/build_desktop_status.py
Desktop status page written to .../data/desktop/aegis_status.html
Status JSON written to .../data/desktop/aegis_status.json

$ python scripts/aegis_agent_gateway.py status
{"ok": true, "command": "status", "data": {"coverage": {"A": "confirmed_tushare", "H": "confirmed_live", "US": "confirmed_live"}, ...}}

$ python scripts/aegis_agent_gateway.py desktop-page
{
  "ok": true,
  "path": "data/desktop/aegis_status.html",
  "absolute_path": ".../data/desktop/aegis_status.html",
  "open_command": "open data/desktop/aegis_status.html"
}

$ python scripts/aegis_agent_gateway.py buy
{"ok": false, "error": "forbidden_command", "command": "buy", "message": "..."}
# exit 1

$ python scripts/openclaw_aegis_readonly.py "aegis status"
{"ok": true, "command": "status", ...}

$ python scripts/openclaw_aegis_readonly.py "aegis holdings"
{"ok": true, "command": "holdings", "data": {"status": "ok", "count": 1, "holdings": [{"symbol": "CRCL", ...}]}}

$ python scripts/openclaw_aegis_readonly.py "aegis buy"
{"ok": false, "error": "forbidden_command", "command": "buy", "message": "..."}
# exit 1
```

Generated HTML (`data/desktop/aegis_status.html`) directly inspected and
confirmed: `translate="no"` on `<html>`/`<body>`, `notranslate` class on
every market/status/code cell, `A股`/`H股`/`美股` labels present,
`已验证` badges for A/H/US coverage with raw values preserved in
`title=`, "A股核心数据...已验证；A股增强数据...增强数据未确认" note
present, "4 条当前未解决缺口" summary with only the fresh "No daily/index
bars returned..." messages, and a collapsed `<details>`"历史数据缺口 /
已被后续验证覆盖（24 条，默认折叠）" block containing only the old
"yfinance package is not installed" messages.

## Real local data referenced (read-only, never modified)

- `data/processed/provider_diagnostics/provider_coverage_report.json` —
  `run_id: provider_diag_20260704_154328`, A daily_bars/index_bars/
  stock_basic/trading_calendar all `pass`; sector_classification/
  fundamentals both `unknown`.
- `data/processed/provider_router/provider_router_live_report.json` —
  unchanged this round, `run_id: provider_router_live_20260704_173128`,
  `pass_count: 4`. **Not run this round** — only read.
- `data/processed/market_snapshot_smoke/market_snapshot_smoke_report.json`
  — H and US both `pass`, `route_snapshot_consistency:
  route_pass_snapshot_pass`.
- `data/records/data_gaps.jsonl` — 28 total rows, untouched (appended-to
  only by prior rounds' real runs, never by this round).
- `config/holdings.yaml` — 1 real holding (CRCL), unchanged.

## Verification against strict non-goals

- No H/US universe/`stock_basic`/sector/fundamentals implemented.
- `UniverseBuilder`, Signal Library, Expert Agents, Decision Engine,
  Recommendation logic: file timestamps confirm untouched.
- `dashboard/index.html`: byte-identical (test-confirmed in three test
  files).
- No broker connection, no real trading, no PaperTrade creation from
  chat/bridge/gateway/adapter.
- No composite/weighted scoring.
- No `.env`/token read, print, grep, or cat anywhere this round.
- CRCL not special-cased — appears only as the one real holding row,
  exactly like any other symbol.

## Next step

Suggested, non-scope-expanding next actions (none require further
approval, but any new scope does):
1. User opens `data/desktop/aegis_status.html` locally to confirm the
   display fixes render correctly in their actual browser.
2. Only with new, explicit approval: the actual OpenClaw skill wiring /
   Feishu bot process that consumes `scripts/openclaw_aegis_readonly.py`,
   or a full H/US Universe design decision.

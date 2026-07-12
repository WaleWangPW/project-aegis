# Project Aegis — P1C Read-Only Bridge + Desktop Status Page — Result

Produced per `Claude_Cowork_P1B4_1_THEN_P1C_DESKTOP_READONLY.md`, Step 2.
Started only after Step 1 (P1B.4.1 smoke consistency fix) was verified
clean: `pytest -v` 364 passed/0 failed, and
`docs/P1B4_MARKETSNAPSHOT_SMOKE_CONSISTENCY_RESULT.md` confirmed the
route/snapshot inconsistency was fixed.

## Goal

Make Project Aegis usable from the desktop and ready for OpenClaw/Feishu
as a **read-only query system** — no H/US universe, no new data source
decisions, no trading, no broker, no PaperTrade creation from an agent,
no composite scoring, no CRCL special-casing.

## What was built

### 1. Desktop status page

- `scripts/build_desktop_status.py` — reads only already-persisted
  files: `config/holdings.yaml`,
  `data/records/{recommendations,paper_trades,reviews,data_gaps}.jsonl`,
  and the latest `provider_router_live_report.json`/
  `market_snapshot_smoke_report.json`. Never fetches live data, never
  triggers a new smoke/validation run, never fabricates P&L/
  recommendations/market status. Any missing source renders an explicit
  `"no_data"` state per section.
- `data/desktop/aegis_status.html` — the rendered page, showing: generated
  timestamp; A/H/US data coverage summary; latest ProviderRouter live
  validation result; latest MarketSnapshot smoke result (including the
  new `route_snapshot_consistency` field from Step 1); holdings summary
  (facts only, no price enrichment, so no fabricated P&L); latest
  recommendations summary; paper trading summary; review summary;
  current data gaps; and a single deterministic, rule-based "next
  operational action" line. Completely separate from
  `dashboard/index.html` — never reads it, never writes to it.
- `data/desktop/aegis_status.json` — the same status dict as a
  machine-readable sidecar, shared by the HTML renderer and every
  `aegis_agent_gateway.py` command that reports status.

### 2. Read-only agent gateway

`scripts/aegis_agent_gateway.py` — the single approved entry point for
an external agent to query Project Aegis.

Allowed commands (all read-only, all return `{"ok": true, "command":
..., "data": ...}` JSON on stdout, exit 0):
`status`, `holdings`, `recommendations`, `paper-summary`,
`review-summary`, `provider-report`, `provider-router-report`,
`market-snapshot-smoke` (reads the persisted report only — never
triggers a new run), `data-gaps`, `desktop-page` (regenerates the
desktop page), `summary` (a condensed top-line view).

Forbidden commands (`buy`, `sell`, `trade`, `order`, `broker`,
`auto-trade`, `rebalance`, `paper-buy`, `paper-sell`,
`create-paper-trade`, `modify-decision`, `modify-recommendation`) are
matched case-insensitively and refused with a structured
`{"ok": false, "error": "forbidden_command", ...}` JSON result and exit
code 1 — never silently ignored, never partially executed. An
unrecognized command that is neither allowed nor explicitly forbidden
also fails closed (`"error": "unknown_command"`, exit 1) rather than
being accepted.

### 3. Optional local server

`scripts/serve_desktop.py` — a minimal static file server for
`data/desktop/`, bound only to `127.0.0.1` (enforced — a non-loopback
`--host` is a controlled argument error), default port `8765`,
directory listing disabled. Verified locally in this sandbox: serves
`aegis_status.html` with `HTTP 200`, refuses a directory listing with
`HTTP 403`. If port 8765 is occupied: `lsof -i :8765` to find the
process, `kill <pid>` to stop it, or pass `--port` to use a different
one (documented in the script's own `--help` and in
`docs/CLI_REFERENCE.md`).

### 4. OpenClaw/Feishu contract doc

`docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md` — states OpenClaw may call
only `scripts/aegis_agent_gateway.py`; must not directly edit JSONL
records; must not read `.env`; must not create `PaperTrade` records;
must not call broker APIs (none exist); Feishu is a read-only
query/notification interface only; CRCL is not special-cased anywhere in
this bridge.

## Design decisions worth recording

- **`market-snapshot-smoke` is read-only by design.** The gateway command
  reads the most recently persisted `market_snapshot_smoke_report.json`
  rather than re-running `scripts/run_market_snapshot_smoke.py` itself —
  running it would mean the gateway triggers outbound network activity
  on an external agent's say-so, which conflicts with "strictly
  read-only". The command's JSON result carries an explicit `"note"`
  field saying so.
- **No price enrichment in the desktop page's holdings section.** Adding
  a live price would require calling `MarketDataService`/`ProviderRouter`
  from a page-generation script, which is out of scope for a "read
  already-persisted files" tool and would risk exactly the kind of
  P&L fabrication the task explicitly forbids if the live call failed
  silently. Holdings are shown as recorded facts only (symbol, shares,
  avg cost, entry date, status) — no computed P&L anywhere on the page.
- **`status` vs `summary`.** `status` returns the full detailed dict
  (including the full holdings list and up to 20 recent data gaps);
  `summary` returns a condensed top-line dict (counts + coverage +
  next action) for a quick check — both are backed by the same
  `build_status()` function so they can never disagree with each other.
- **`build_desktop_status.py` and `aegis_agent_gateway.py` share all
  logic.** The gateway never re-implements the summary-building code —
  it imports `scripts.build_desktop_status` and calls its functions
  directly, so the desktop page and every gateway command are
  guaranteed to report the same numbers from the same inputs.

## Tests added

`tests/test_build_desktop_status.py` (9 tests): every section renders an
honest `"no_data"` state when nothing exists; holdings summary reads
real holdings with no fabricated P&L fields; provider-router-live/smoke
reports are read, not recomputed; a malformed report JSON is treated as
`"no_data"`, not a crash; HTML rendering escapes content and never
raises on a fully-empty status; `dashboard/index.html` unchanged; no
`.env`/token/`ProviderRouter`/`yfinance` usage; no broker/PaperTrade
construction; `main()` writes both output files correctly.

`tests/test_aegis_agent_gateway.py` (39 tests collected, most from
parametrization by command): every one of the 11 allowed commands returns
`{"ok": true, ...}` and exit 0 with JSON-serializable data; every one of
the 12 forbidden commands is refused with exit 1 (plus a
case-insensitivity check); an unknown command fails closed; `holdings`
returns real holdings including CRCL as an ordinary row;
`market-snapshot-smoke` carries the read-only `"note"`; `desktop-page`
actually writes both output files; `summary` is condensed to the
expected key set; the CLI's `main()` returns the right exit codes for
both an allowed and a forbidden command; the allowed/forbidden command
sets exactly match the task spec; `dashboard/index.html` unchanged; no
`.env`/token/broker/PaperTrade-construction usage; no CRCL
special-casing (checked via absence of any conditional keyed on the
literal string, not a bare substring check).

**pytest -v: 412 passed, 0 failed** (364 + 48: 9 in
`tests/test_build_desktop_status.py`, 39 in the parametrized
`tests/test_aegis_agent_gateway.py` — 11 allowed-command cases + 12
forbidden-command cases + 3 case-insensitivity cases + 13 targeted
tests; see exact count in `docs/DEVELOPMENT_STATUS.md`).

## Verified commands

```bash
python scripts/build_desktop_status.py
# Desktop status page written to .../data/desktop/aegis_status.html
# Status JSON written to .../data/desktop/aegis_status.json

python scripts/aegis_agent_gateway.py status     # {"ok": true, ...}, exit 0
python scripts/aegis_agent_gateway.py holdings   # {"ok": true, "data": {"count": 1, ...CRCL...}}, exit 0
python scripts/aegis_agent_gateway.py summary    # {"ok": true, "data": {...}}, exit 0
python scripts/aegis_agent_gateway.py buy        # {"ok": false, "error": "forbidden_command", ...}, exit 1
python scripts/aegis_agent_gateway.py create-paper-trade  # refused, exit 1

python scripts/serve_desktop.py --port 8765
# curl http://127.0.0.1:8765/aegis_status.html -> HTTP 200
# curl http://127.0.0.1:8765/                   -> HTTP 403 (directory listing disabled)
```

Real sandbox output of `data/desktop/aegis_status.json`'s top-level
sections (holdings genuinely present — the real CRCL holding from
`config/holdings.yaml`; recommendations/paper trading/review honestly
`no_data` since none exist in this sandbox yet; provider_router_live
`ok` reflecting the user's real local pass result; market_snapshot_smoke
`ok` reflecting this sandbox's honest `dependency_missing` result from
Step 1's verification run).

## Explicit non-goals confirmed untouched this round

No H/US universe, no H/US `stock_basic`, no sector/fundamentals, no
`UniverseBuilder`/Signal Library/Expert Agents/Decision Engine/
Recommendation logic changes, `dashboard/index.html` byte-identical
(confirmed by tests in both new test files), no real trading, no broker
connection or reference anywhere in the new code, no `PaperTrade`
creation from the gateway (verified: no `PaperTrade(` construction call
in either new script), no composite/weighted scoring, no `.env`/token
read/print/grep/cat (verified: neither new script imports a provider
adapter, `os.environ`, or `dotenv` at all), CRCL not special-cased
(verified: no conditional logic anywhere keyed on the literal string
`"CRCL"` in either new script — it only ever appears as whatever
already-persisted data happens to contain it, e.g. the one real holding
in `config/holdings.yaml`).

## Known gaps

`data/records/recommendations.jsonl`, `paper_trades.jsonl`, and
`reviews.jsonl` do not yet exist in this repository (no real
recommendation pipeline run has been performed against real Tushare
data), so the desktop page's recommendations/paper-trading/review
sections currently show their honest empty states — this is expected
given the project's current phase, not a P1C bug. The actual OpenClaw
skill wiring and Feishu bot implementation that would *consume* this
contract are intentionally out of scope for this round (see
`docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md`'s closing section).

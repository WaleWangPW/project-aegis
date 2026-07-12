# Project Aegis — Data & Records

Phase 8 deliverable. Documents what lives under `data/`, what each
directory is for, what's append-only/audit-critical vs. safe to delete
and rebuild, and how backtest output stays isolated from live records.
Reflects the real `data/` tree as it exists in this repository as of
Phase 8 (see the tree at the bottom).

## Directory overview

### `data/raw/`

Placeholder for any raw provider payloads that might be cached verbatim
in a future phase. Currently unused (only a `.gitkeep`). Safe to delete
and recreate empty at any time — nothing in the current codebase reads
from it.

### `data/cache/`

CSV cache written by `aegis/data/cache.py::DataCache`, keyed by
market/data_type/key. Purely a performance optimization over repeated
Tushare calls — every reader falls back to calling the provider again on
a cache miss. **Safe to delete and rebuild** at any time; deleting it
never loses information, it only costs an extra provider round-trip next
time that data is requested.

**`data/cache/calendar/{market}/trading_calendar.csv`** (introduced
P1A) — a separate, dedicated cache written by
`aegis/calendar/repository.py::TradingCalendarRepository`, one file per
market (`A`/`H`/`US`), columns `date` ("YYYY-MM-DD") and
`is_trading_day` (0/1). `TradingCalendarService` reads this first before
falling back to the live provider or (only if explicitly enabled) a
conservative Mon-Fri assumption. **Safe to delete and rebuild** — it is
always repopulated from the provider on the next call, same as every
other file under `data/cache/`.

### `data/processed/`

Derived, re-computable artifacts:

- `<date>/{decisions,recommendations}_pre_market.json` — a snapshot dump
  written by `run_pre_market.py` alongside (not instead of) the
  authoritative JSONL rows in `data/records/`.
- `reviews_<start>_<end>.{md,json}` — reports written by
  `scripts/export_review.py`, always derivable again from
  `data/records/reviews.jsonl` for the same date range.
- `backtests/<run_id>/` — see the dedicated section below.
- `provider_diagnostics/provider_coverage_report.json` (introduced P1A;
  status vocabulary hardened P1A.1) — written by
  `scripts/validate_real_data.py`; a `ProviderCoverageReport` (see
  `docs/CLI_REFERENCE.md`'s `validate_real_data.py` section for the full
  schema) documenting which P0 data categories a real Tushare account
  actually supports for A/H/US. Always overwritten by the next run, never
  appended to — re-derivable at any time by re-running the script against
  a real token. The first real (non-sandbox) run of this file's contents
  is interpreted in `docs/P1A_REAL_DATA_VALIDATION_RESULT.md` and
  `docs/P1A_PROVIDER_COVERAGE_DECISION.md`. **P1C.1**:
  `scripts/build_desktop_status.py` (and, through it,
  `scripts/aegis_agent_gateway.py`'s `status`/`desktop-page`/`summary`/
  `data-gaps` commands) now also reads this file to derive A股's core
  coverage verdict — `daily_bars`/`index_bars`/`stock_basic`/
  `trading_calendar` all `pass` → `A股: 已验证` (raw value
  `confirmed_tushare`) on the desktop page/gateway. Only ever reads
  `market == "A"` checks from this file; H/US entries here predate P1B's
  ProviderRouter route and are deliberately never used as H/US's
  coverage signal (that still comes only from
  `provider_router_live_report.json` + `market_snapshot_smoke_report.json`,
  below). Read-only — this round never re-runs
  `scripts/validate_real_data.py` or writes to this file.
- `provider_diagnostics/provider_router_report.json` (introduced P1B.1)
  — written by `scripts/check_provider_router.py`; a config + wiring
  sanity report (route table, symbol-mapping validation, package
  availability) for `ProviderRouter` (`aegis/data/provider_router.py`).
  Not a live coverage report — see `docs/P1B1_PROVIDER_ROUTER_RESULT.md`.
  Always overwritten by the next run.
- `provider_router/provider_router_live_report.json` (introduced P1B.2)
  — written by `scripts/validate_provider_router_live.py`; a live
  validation report for `ProviderRouter`'s H/US **secondary**
  (`yahoo_finance`) route only (daily bars, index bars, stock_basic).
  Never touches Tushare/`.env`/`os.environ`/`TUSHARE_TOKEN` — see
  `docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md`. Current
  contents are from the user's **real local run** (real `yfinance` +
  network, not this Cowork sandbox): H/US daily bars and index bars all
  `pass` (including CRCL), both `stock_basic` checks correctly
  `not_configured` (intentional, not a gap). **Always overwritten by the
  next run of the script** — this file is a live snapshot, not an
  append-only record. This has now happened **twice** from inside this
  Cowork sandbox: once during the first P1B.3 implementation round, and
  again during the P1B.4 local smoke failure triage round (run as part
  of verifying "live validation still passes"); both times caught
  immediately and restored verbatim from the JSON captured in
  `docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md` (see
  `docs/HANDOFF.md` for both incidents). **Do not run
  `scripts/validate_provider_router_live.py` against its default output
  path from this sandbox** — if it must be run at all, pass an explicit
  `--output` pointed somewhere disposable, and never assume the default
  report file is safe to overwrite here.
- `market_snapshot_smoke/market_snapshot_smoke_report.json` (introduced
  P1B.4, extended P1B.4.1) — written by
  `scripts/run_market_snapshot_smoke.py`; a smoke report proving
  `MarketSnapshotService`/`MarketRegimeAnalyzer` (Phase 2, unmodified)
  actually consume H/US daily/index bars through `MarketDataService` +
  `ProviderRouter`'s `yahoo_finance` route. Bars dated after the run's
  `--date` are filtered out before analysis (never fabricated, never
  included). P1B.4.1 added `index_bars_usable`/`daily_bars_usable`
  (bool) and a per-market `route_snapshot_consistency` field
  (`route_pass_snapshot_pass`/`route_pass_snapshot_partial`/
  `route_fail_snapshot_unknown`, or an explicitly-labeled
  `inconsistent_*` state that should be structurally impossible now) —
  see `docs/P1B4_MARKETSNAPSHOT_SMOKE_CONSISTENCY_RESULT.md`. **As of
  P1C.3, current contents are the user's real, locally-confirmed H/US
  `pass` result** (`run_id: market_snapshot_smoke_20260705_054604`, both
  H and US `overall_status: pass`, 41 real rows each) — this is what the
  desktop page's/gateway's H/US `confirmed_live` coverage is built on.
  **This file is overwritten by the next run of the script, so it is no
  longer safe to re-run from a sandbox with no `yfinance`/network** (the
  P1D round did exactly this by accident, overwriting it with a
  degraded `dependency_missing` result, then restoring it byte-for-byte
  from the stock-agent workspace mirror copy — see
  `docs/P1D_REAL_PREMARKET_PIPELINE_SMOKE_RESULT.md`). Treat this file
  with the same caution as `provider_router_live_report.json`: don't
  re-run `scripts/run_market_snapshot_smoke.py` against its default
  `--output` path from a sandbox without real `yfinance`/network unless
  you first confirm a restore point exists (the stock-agent workspace
  mirror, refreshed by `scripts/refresh_stock_agent_aegis_status.py`, is
  one such copy).

**Safe to delete and rebuild** — every file here is a derived report or
snapshot; the authoritative source of truth for anything it summarizes
lives in `data/records/` (for live pipeline output) or is
self-contained within its own `<run_id>`/report (for backtests and
provider diagnostics).

### `data/records/`

**Audit-critical, append-only.** The authoritative JSONL storage for the
live decision pipeline:

| File | Written by | Model |
|---|---|---|
| `market_snapshots.jsonl` | `MarketSnapshotService` | `MarketSnapshot` |
| `candidates.jsonl` | `UniverseBuilder`/`run_pre_market.py` | `Candidate` |
| `signals.jsonl` | `compute_signals_for_candidate`/`run_pre_market.py` | `Signal` |
| `expert_opinions.jsonl` | `ExpertCommittee`/`run_pre_market.py` | `ExpertOpinion` |
| `decisions.jsonl` | `RecommendationService`/`run_pre_market.py` | `DecisionRecord` |
| `recommendations.jsonl` | `RecommendationService`/`run_pre_market.py` | `RecommendationRecord` (the canonical object, ADR-001) |
| `paper_trades.jsonl` | `PaperTradeService`/`run_pre_market.py`/`run_close.py` | `PaperTrade` (virtual only, never a real order) |
| `reviews.jsonl` | `ReviewService`/`run_close.py` | `ReviewRecord` |
| `investment_memory.jsonl` | `MemoryService`/`run_close.py` | `InvestmentMemory` |
| `data_gaps.jsonl` | `DataGapRegistry` (used everywhere data is missing/unavailable) | gap record — as of P1B.3, `MarketDataService`'s gaps label `provider` with the actual failing route (`"tushare"`, `"yahoo_finance"`, or a generic fallback if no route is configured at all, via `ProviderRouter.route_name_for`), embed the failing exception's type in `message`, and always populate `consumer_impact`. **P1C.1**: never deleted or rewritten by the desktop page/gateway — the display layer only (`_split_stale_gaps` in `scripts/build_desktop_status.py`) separates a stale, now-superseded `yfinance package is not installed` gap (message matches a known stale marker, its market is currently confirmed by a later report, and its own `created_at` predates that report's) from every other current gap; the underlying file is untouched either way. **P1C.3**: the stale-marker match was broadened — `_STALE_GAP_MESSAGE_MARKERS` now also matches `"dependency_missing"`/`"network_unavailable"`, and a new `_STALE_GAP_EMPTY_ROUTE_MARKERS` set (`"no daily bars returned"`/`"no index bars returned"`/`"empty result"`) matches only when the message also names the route explicitly (`"via provider_route='yahoo_finance'"`), plus a structural gate (`provider=="yahoo_finance"`, `data_type in {index_bars,daily_bars}`, `market in {H,US}`) — this now correctly supersedes the real HSI.HI/SPX/00700.HK/CRCL gaps whose message text never matched the original P1C.1 marker. The file itself is still **never deleted or rewritten** by this display-layer change |

Every row here is meant to persist indefinitely — this is the system's
decision history and the only place `recommendation_id` linkage can be
traced end to end (see `docs/P0_ACCEPTANCE_REPORT.md` criterion 15).
**Do not delete this directory** in a real deployment.

**P1D update**: `python scripts/run_pre_market.py --date 2026-07-06` was
run for real in this Cowork sandbox for the first time, producing the
project's first real entries in `market_snapshots.jsonl`,
`candidates.jsonl`, `signals.jsonl`, `expert_opinions.jsonl`,
`decisions.jsonl`, and `recommendations.jsonl` (all still linked by ID —
one `DecisionRecord`/`RecommendationRecord` for CRCL, `status: "Exit"`,
via the Decision Engine's existing Risk-veto rule, since no real
Tushare token/`yfinance`/network exists here). `paper_trades.jsonl` and
`reviews.jsonl` still do not exist — no `Action` recommendation has ever
fired (so `PaperTradeService` never opened a trade), and
`scripts/run_close.py` (which generates reviews) has not been run.

`update()`-style operations (e.g. `PaperTradeRepository.update()`) are
implemented as a safe read-all/rewrite-all over the whole JSONL file,
since JSONL itself has no native "update one row" operation — this is
still append-only in spirit (nothing is ever partially corrupted; a
failed rewrite would leave the previous file intact until the new one is
fully written).

### `data/desktop/` (introduced P1C, polished P1C.1)

- `aegis_status.html` — the read-only desktop status page built by
  `scripts/build_desktop_status.py` (or regenerated via
  `scripts/aegis_agent_gateway.py desktop-page`). Completely separate
  from `data/dashboard/dashboard_data.json`/`dashboard/index.html` — it
  is never read by the dashboard and never writes to it. **P1C.1**: the
  whole document is `translate="no"`/`notranslate`-protected (document,
  `<body>`, and every individual market-code/status-badge/run_id/
  timestamp/symbol/data_type cell), so browser translation tools can no
  longer mangle short tokens like `A`/`US` into unrelated Chinese words.
  Market codes render as `A股`/`H股`/`美股`; status tokens render as
  human Chinese labels (已验证/未确认/暂无数据/通过/部分通过/依赖缺失/
  网络不可用/未配置) with the raw enum value preserved only in a
  non-translated `title=` attribute.
- `aegis_status.json` — the same status dict as a machine-readable
  sidecar, shared by the HTML renderer and every `aegis_agent_gateway.py`
  command that reports status, so the two can never drift apart. Raw
  enum values only — the human-label mapping above is a display-only
  concern of the HTML renderer; this JSON file's field names/values are
  unaffected by P1C.1.

**Safe to delete and rebuild** — both files are always fully
re-derivable from `config/holdings.yaml` + `data/records/` + the latest
`provider_router_live_report.json`/`market_snapshot_smoke_report.json`;
nothing here is itself a source of truth.

### `docs/openclaw/` (introduced P1C.2)

- `docs/openclaw/project-aegis-readonly/SKILL.md` — a documentation
  scaffold describing the read-only command contract an OpenClaw skill
  or Feishu bot must follow (command examples, exact shell command,
  forbidden-command list, expected JSON, refusal behavior). **Not**
  code, **not** a registered/running OpenClaw skill, and **not** read by
  any script in this repo — purely a reference document for whoever
  wires up the actual integration. Safe to delete/regenerate at any
  time; it contains no state, only a description of
  `scripts/openclaw_aegis_readonly.py`'s already-implemented contract.

**P1C.2 also confirms**: `data/records/paper_trades.jsonl` is never
created or modified by any OpenClaw/Feishu-facing command — the
forbidden commands (`buy`, `paper-buy`, `paper-sell`,
`create-paper-trade`, etc.) are refused by
`scripts/aegis_agent_gateway.py` before any handler code runs, and
`scripts/check_openclaw_aegis_readonly.py` proves this by fingerprinting
the file (`mtime` + `sha256`) immediately before and after invoking the
forbidden command — not just trusting the JSON refusal response.

### `~/.openclaw/agents/stock-agent/workspace/project-aegis/` (introduced P1C.3, outside this repo)

- Not part of this repo — lives under the user's home directory. A
  **read-only mirror**, rebuilt on demand by
  `scripts/refresh_stock_agent_aegis_status.py`, so the Feishu/OpenClaw
  stock-agent can answer `aegis status`/`holdings`/`summary` by reading
  a plain file — no `exec`, no `nodes.invoke`, no localhost `web_fetch`
  dependency.
- Contains: `aegis_status.json`/`.html` (copies of the files in
  `data/desktop/`), plus `market_snapshot_smoke_report.json`/
  `provider_router_live_report.json`/`provider_coverage_report.json`
  (each copied only if it already exists in the repo), and a
  `README_FOR_STOCK_AGENT.md` restating the read-only rules (no
  PaperTrade, no broker, no CRCL special-casing, don't edit these files
  directly — they're overwritten on the next refresh).
- **Safe to delete and rebuild** — every file here is a copy; re-running
  `python scripts/refresh_stock_agent_aegis_status.py` regenerates all
  of it. Never contains a token/secret; the refresh script never reads
  `.env`.

### `data/dashboard/`

- `dashboard_data.json` — the single file `dashboard/index.html` actually
  reads at runtime. Always fully regenerable from `data/records/` +
  `config/holdings.yaml` via `DashboardBuilder`/`scripts/build_dashboard.py`.
  **Safe to delete and rebuild.**

`dashboard/index.html` itself lives one directory up
(`workstations/stock-trading/projects/project-aegis/dashboard/index.html`,
mirrored byte-for-byte into `repo/dashboard/index.html`) — it is UI code,
not data, and is never written to by any script in this repository.

### `data/processed/backtests/<run_id>/` — backtest isolation

Introduced Phase 7. Every `TimeTravelEngine`/`scripts/run_backtest.py` run
writes exclusively here, under a unique `run_id` (e.g.
`bt_20260704T073051854041`), and **never** touches `data/records/`:

| File | Contents |
|---|---|
| `backtest_results.jsonl` | one `BacktestResult` per `freeze_date` replayed |
| `metrics_report.json` / `metrics_report.md` | aggregated `MetricsReport` for the whole run |
| `data_access_log.jsonl` | every `HistoricalDataProvider` read, tagged `stage="decision"` or `stage="evaluation"` — the audit trail proving no future data was served during decision stage |
| `data_gaps.jsonl` | `DataGap` records specific to this backtest run (a separate `DataGapRegistry` instance from the live one) |

This isolation is enforced in code (`TimeTravelEngine`/
`BacktestRepository` only ever construct paths under
`data/processed/backtests/<run_id>/`) and verified by tests:
`tests/test_backtest_boundaries.py::test_backtest_engine_never_writes_to_live_records_directory`,
`tests/test_run_backtest.py::test_run_backtest_never_writes_to_live_records_dir`,
and `tests/test_time_travel_engine.py::test_run_date_output_isolated_under_backtests_directory_not_records`.

**Safe to delete** — a `<run_id>` directory is a self-contained report of
one historical replay; deleting it loses that specific report but never
affects live decision history or any other run's output. No backtest run
has been performed against the real repository root yet in this Cowork
sandbox (only under `tmp_path` in tests) — this directory does not exist
under the real `data/` tree as of Phase 8.

## `DataGap` behavior

`DataGapRegistry` (`aegis/data/gaps.py`) appends structured gap records
(`severity`: `info`/`warning`/`error`) to a JSONL file whenever real data
is missing, unavailable, or would require serving something dishonest.
This is the project-wide alternative to fabricating a value: every
signal, agent, dashboard field, and backtest read that can't get real
data records a `DataGap` (or an explicit `DATA_GAP:`-prefixed fallback
string) instead of guessing. Live-pipeline gaps go to
`data/records/data_gaps.jsonl`; backtest-run gaps go to that run's own
`data/processed/backtests/<run_id>/data_gaps.jsonl` — never mixed.

## What's safe to delete vs. audit-critical — quick reference

| Path | Safe to delete? | Why |
|---|---|---|
| `data/raw/` | Yes | Unused placeholder |
| `data/cache/` | Yes | Pure performance cache, always rebuildable from the provider |
| `data/processed/<date>/*.json` | Yes | Derived snapshot dump alongside the authoritative JSONL |
| `data/processed/reviews_*.{md,json}` | Yes | Derived report, re-exportable from `data/records/reviews.jsonl` |
| `data/processed/backtests/<run_id>/` | Yes | Self-contained historical replay report, isolated from live history |
| `data/processed/provider_diagnostics/provider_coverage_report.json` | Yes | Re-derivable by re-running `scripts/validate_real_data.py` |
| `data/processed/provider_diagnostics/provider_router_report.json` | Yes | Re-derivable by re-running `scripts/check_provider_router.py` |
| `data/processed/provider_router/provider_router_live_report.json` | Yes | Re-derivable by re-running `scripts/validate_provider_router_live.py` |
| `data/processed/market_snapshot_smoke/market_snapshot_smoke_report.json` | Yes | Re-derivable by re-running `scripts/run_market_snapshot_smoke.py` |
| `data/cache/calendar/{market}/trading_calendar.csv` | Yes | Repopulated from the provider on next use |
| `data/records/*.jsonl` | **No** | Authoritative append-only decision history; the only source of `recommendation_id` linkage |
| `data/dashboard/dashboard_data.json` | Yes | Always regenerable from `data/records/` + `config/holdings.yaml` |
| `dashboard/index.html` | **Never** — not data, this is the UI itself | Must remain byte-identical per every phase's own constraint |

## Real `data/` tree as of Phase 8

```text
data/
├── cache/.gitkeep
├── dashboard/
│   ├── .gitkeep
│   └── dashboard_data.json      # real, empty-state (no real Tushare data yet)
├── processed/
│   ├── .gitkeep
│   └── reviews_20260701_20260731.md   # real, empty-state export from Phase 6
├── raw/.gitkeep
└── records/.gitkeep              # empty — no real pipeline run has populated this yet
```

No `data/processed/backtests/` directory exists under the real repo root
— every backtest test uses an isolated `tmp_path`, and no real
`scripts/run_backtest.py` invocation has been made against this repo yet
(no real Tushare network in this Cowork sandbox). The same is true of
`data/processed/provider_diagnostics/` and `data/cache/calendar/`
(introduced P1A) — every `scripts/validate_real_data.py` and
`TradingCalendarService` test runs against an isolated `tmp_path`; no
real run has populated these directories under the real repo root yet.
See `docs/HANDOFF.md`'s `TODO_FOR_USER` note for the local command to run
once a real `TUSHARE_TOKEN` is available.

# Project Aegis — CLI Reference

Phase 8 deliverable. Documents every script under `scripts/` as it
actually behaves today — purpose, example command, inputs, outputs,
failure behavior, and the phase it was introduced in. All `--help` output
below was captured directly from the real scripts this phase.

None of these scripts place a real order, connect to a real broker, or
call the live Tushare network by default in tests (every script accepts
an injectable fake provider in its testable core function). Only
`check_tushare.py` and the real (non-test) invocation of the pipeline
scripts touch `TushareAdapter.from_env()`, and only when no fake provider
is supplied.

## `scripts/check_tushare.py`

**Purpose:** Verify `TUSHARE_TOKEN` is configured and that a minimal,
cheap Tushare call (a 2-day trading-calendar window) succeeds — without
ever printing the token value. Introduced Phase 1.

**Example:**

```bash
python scripts/check_tushare.py
```

**Inputs:** `TUSHARE_TOKEN` environment variable (or `.env` file, loaded
via `python-dotenv`). No CLI flags.

**Outputs:** A short status message to stdout, one of:

```text
TUSHARE_TOKEN: missing
Set TUSHARE_TOKEN in .env or environment. Token value was not printed.
```

```text
TUSHARE_TOKEN: configured
TushareAdapter: initialized
Basic provider check: OK
```

```text
TUSHARE_TOKEN: configured
TushareAdapter: initialized
Basic provider check: FAILED (<ProviderError message>)
```

**Failure behavior:** Exits 1 if the token is missing or the provider call
raises a controlled `ProviderError`; exits 0 only on a real, successful
provider round-trip. Verified this phase with `TUSHARE_TOKEN` unset —
printed the "missing" message and exited 1, no token ever touched.

## `scripts/run_pre_market.py`

**Purpose:** The pre-market decision pipeline. Builds MarketSnapshots,
Candidates, Signals, ExpertOpinions, DecisionRecords, and
RecommendationRecords for a given date/market set; writes the Dashboard
JSON; opens a virtual PaperTrade for every freshly-generated Action
recommendation. Introduced Phase 2, extended every phase through Phase 6.

**Example:**

```bash
python scripts/run_pre_market.py --date 2026-07-04 --markets A,H,US
```

**Inputs:**

```text
usage: run_pre_market.py [-h] --date DATE [--markets MARKETS]

--date DATE         YYYY-MM-DD (required)
--markets MARKETS   Comma-separated, e.g. A,H,US (default: A,H,US)
```

Reads `config/holdings.yaml`, `config/universe.yaml`, `config/experts.yaml`,
`config/decision_rules.yaml`; calls Tushare (real or injected fake
provider) for bars/index bars/stock lists/fundamentals.

**Outputs:** `data/processed/<date>/{decisions,recommendations}_pre_market.json`,
appends to `data/records/{decisions,recommendations,paper_trades}.jsonl`,
rebuilds `data/dashboard/dashboard_data.json`. Never writes
`dashboard/index.html`; never generates Review/Memory/Backtest artifacts
(those are `run_close.py`'s and `run_backtest.py`'s jobs).

**Failure behavior:** A Dashboard-build failure or PaperTrade-creation
failure is captured on the result object (`dashboard_error`/
`paper_trade_error`) and reported in the printed summary — it never hides
already-persisted recommendations. Empty candidates (e.g. `--markets ""`)
produce an honest empty result, not a crash.

**P1D note:** run for real for the first time in this Cowork sandbox
(`python scripts/run_pre_market.py --date 2026-07-06`) — needed no code
change. With no `TUSHARE_TOKEN`/`yfinance`/network available, it
produced an honest, fully-linked `Exit` recommendation for CRCL (the
only real holding) driven by the Decision Engine's existing Risk-veto
rule — proof the pipeline degrades safely end-to-end rather than
crashing or fabricating data. See
`docs/P1D_REAL_PREMARKET_PIPELINE_SMOKE_RESULT.md`.

## `scripts/build_dashboard.py`

**Purpose:** Standalone Dashboard JSON builder — reads existing
MarketSnapshot/RecommendationRecord/PaperTrade/Review JSONL rows plus
`config/holdings.yaml`, and writes a schema-validated
`dashboard_data.json`. Never recomputes any upstream step. Introduced
Phase 5.

**Example:**

```bash
python scripts/build_dashboard.py --date 2026-07-04 --session pre_market
```

**Inputs:**

```text
usage: build_dashboard.py [-h] --date DATE [--session SESSION]
                          [--output OUTPUT] [--records-dir RECORDS_DIR]
                          [--holdings-config HOLDINGS_CONFIG]

--date DATE                      YYYY-MM-DD (required)
--session SESSION                default: pre_market
--output OUTPUT                  default: data/dashboard/dashboard_data.json
--records-dir RECORDS_DIR        default: data/records
--holdings-config HOLDINGS_CONFIG default: config/holdings.yaml
```

**Outputs:** A single validated `dashboard_data.json` file at `--output`.

**Failure behavior:** Catches `pydantic.ValidationError` and any other
exception, prints a controlled error to stderr, and exits non-zero rather
than writing a partial/invalid file.

## `scripts/run_close.py`

**Purpose:** The end-of-day pipeline. Updates every open PaperTrade's
forward returns/drawdown -> generates any newly-due Reviews -> appends
minimal Investment Memory lessons -> rebuilds the Dashboard JSON.
Introduced Phase 6.

**Example:**

```bash
python scripts/run_close.py --date 2026-07-04
```

**Inputs:**

```text
usage: run_close.py [-h] --date DATE [--data-dir DATA_DIR]

--date DATE           YYYY-MM-DD (required)
--data-dir DATA_DIR   Override the data/ directory (default: <repo_root>/data)
```

Reads `data/records/paper_trades.jsonl`, `config/holdings.yaml`.

**Outputs:** Rewrites `data/records/paper_trades.jsonl` (updated forward
returns), appends `data/records/reviews.jsonl` and
`data/records/investment_memory.jsonl`, rebuilds
`data/dashboard/dashboard_data.json`.

**Failure behavior:** With no open PaperTrades (e.g. a real, empty
`data/records/`), prints an honest empty summary (`updated_trades: 0`,
`generated_reviews: 0`) and exits 0 — never crashes. A dashboard-rebuild
failure is reported separately, never allowed to hide the trade/review
updates that already succeeded. Verified this phase's predecessor phase
with a real run against empty `data/records/`.

## `scripts/export_review.py`

**Purpose:** Exports a factual review report over an existing date range
— reads `ReviewRecord`s only, never re-reviews anything. Introduced
Phase 6.

**Example:**

```bash
python scripts/export_review.py --start 2026-07-01 --end 2026-07-31 --format md
```

**Inputs:**

```text
usage: export_review.py [-h] --start START --end END [--format {md,json}]
                        [--records-dir RECORDS_DIR] [--output-dir OUTPUT_DIR]

--start START               YYYY-MM-DD (required)
--end END                   YYYY-MM-DD (required)
--format {md,json}          default: md
--records-dir RECORDS_DIR   default: data/records
--output-dir OUTPUT_DIR     default: data/processed
```

**Outputs:** `data/processed/reviews_<start>_<end>.{md,json}` — plain
factual report (review count, Action success rate, average return, max
drawdown, market/sector breakdown, lessons, explicit `DATA_GAP`/
inconclusive counts). No marketing language, no fabricated conclusions.

**Failure behavior:** An empty review range produces an honest empty
report ("尚无复盘记录", `DATA_GAP: 无可用数据` for every metric), never a
crash or a fabricated stat.

## `scripts/run_backtest.py`

**Purpose:** Time Travel Backtest — historical replay of the exact same
deterministic Phase 2-4 decision pipeline (MarketSnapshot -> Universe ->
Signals -> Expert Committee -> Decision Engine) under a frozen
`freeze_date`, with `HistoricalDataProvider` enforcing that decision-stage
code can never read data dated after `freeze_date`. Forward 5/10/20/40
trading-day returns are only computed after recommendations are finalized
(evaluation stage). Introduced Phase 7.

**Example:**

```bash
python scripts/run_backtest.py --start 2026-06-01 --end 2026-06-30 --markets A,H,US
```

**Inputs:**

```text
usage: run_backtest.py [-h] --start START --end END [--markets MARKETS]
                       [--session SESSION] [--data-dir DATA_DIR]

--start START         YYYY-MM-DD (required)
--end END             YYYY-MM-DD (required)
--markets MARKETS     Comma-separated, e.g. A,H,US (default: A,H,US)
--session SESSION     default: close
--data-dir DATA_DIR   default: <repo_root>/data
```

**Outputs:** Everything is written under the isolated
`data/processed/backtests/<run_id>/` directory — **never**
`data/records/` (live records are never touched):

- `backtest_results.jsonl` — one `BacktestResult` per `freeze_date`
- `metrics_report.json` / `metrics_report.md`
- `data_access_log.jsonl` — every `HistoricalDataProvider` access, for
  auditing that no future data was read during the decision stage

**Failure behavior:** Rejects a malformed date range or unknown market
before doing any work (`BacktestArgumentError`, printed to stderr, exit
1) — never a raw traceback. **Exits 0 only if
`no_future_data_violations == 0` across the entire run; exits 1
otherwise** — this is the CLI's own hard gate on the no-leakage guarantee,
not just a warning.

## `scripts/validate_real_data.py`

**Purpose:** P1A real-data provider-coverage diagnostics. Verifies
`TUSHARE_TOKEN` presence (without ever printing it), runs a cheap
connectivity probe, then exercises every P0 data category (A/H/US daily
bars, index bars, stock basic list, sector classification, fundamentals,
trading calendar) against the real Tushare provider and writes a
structured coverage report. Never turns provider availability into a
recommendation. Introduced P1A.

**Example:**

```bash
python scripts/validate_real_data.py
python scripts/validate_real_data.py --markets A,H,US
python scripts/validate_real_data.py --output data/processed/provider_diagnostics/provider_coverage_report.json
```

**Inputs:**

```text
usage: validate_real_data.py [-h] [--markets MARKETS] [--date DATE]
                             [--output OUTPUT]

--markets MARKETS   Comma-separated, e.g. A,H,US (default: A,H,US)
--date DATE         YYYY-MM-DD (default: today, UTC)
--output OUTPUT     default: data/processed/provider_diagnostics/provider_coverage_report.json
```

**Outputs:** A single `ProviderCoverageReport` JSON file at `--output`,
matching the schema in `docs/DATA_AND_RECORDS.md` — `run_id`,
`token_present`, `network_available`, one `checks[]` entry per
market/category, and a `summary` with per-status counts plus
`critical_gaps`.

**P1A.1 hardened status vocabulary** (`checks[].status`, replacing the
plain P1A four-value set):

- `pass` — succeeded, returned rows, not flagged as a cross-market
  duplicate.
- `fail` — a real `ProviderError` with no permission/quota signature.
- `permission_denied` — a real `ProviderError` whose message looks
  entitlement/permission/quota related (never inspects/logs the token).
- `skipped` — the provider object doesn't implement this method.
- `not_configured` — a required input (e.g. a per-market sample symbol)
  has no configured value; the call was never attempted.
- `unknown_empty` — succeeded but returned zero rows (was called
  `unknown` pre-P1A.1; same meaning, clearer name).
- `unsupported` — P1A.1 hardening: a non-A股 market's check reported
  "pass" with the **exact same `rows_returned` as A股's** check for the
  same `data_type` (currently applied to `stock_basic` only — see
  `docs/P1A_PROVIDER_COVERAGE_DECISION.md`). This is the real bug
  observed against the live Tushare token: `TushareAdapter.get_stock_basic`
  ignores its `market` argument and always returns the SSE/SZSE list, so
  H/US `stock_basic` naively "passing" with A股's row count is never
  confirmed real H/US coverage. Downgraded from `pass` before the report
  is finalized, and always recorded as a `DataGap` too — never silently
  dropped.

`summary` fields: `pass_count`, `fail_count`, `skipped_count`,
`unknown_count` (counts `unknown_empty` checks — field name kept for
backward compatibility), `unsupported_count`, `permission_denied_count`,
`not_configured_count`, `critical_gaps` (lists every `fail`/
`permission_denied` check's `check_name` — `unsupported`/`not_configured`
are expected/structural, not "critical", but are still fully recorded via
`DataGap`, never hidden).

**Failure behavior:** Missing `TUSHARE_TOKEN` → prints a safe message
(never the token), exits 1, but still writes an honest empty-state report
(`token_present: false`, zero checks) rather than nothing at all. Token
present but the connectivity probe fails → writes a report with every
check marked `"skipped"` and one shared reason, exits 0 (a documented
degrade, not a CLI error). Token present and reachable → real per-category
results (now using the hardened status vocabulary above), exits 0
regardless of how many checks failed (a failed *check* is honest
diagnostic data, not a script failure). Verified this phase with
`TUSHARE_TOKEN` unset: printed the safe missing message, exited 1, and
still wrote a valid empty-state JSON report.

**Real-data run (P1A.1):** The user has since run this script locally
with a real `TUSHARE_TOKEN` + network. Results, reconciliation, and the
resulting coverage decision are in
`docs/P1A_REAL_DATA_VALIDATION_RESULT.md` and
`docs/P1A_PROVIDER_COVERAGE_DECISION.md`. Summary: A股 core data path
(daily bars, index bars, stock_basic, trading calendar) is confirmed;
H/US/CRCL and sector/fundamental coverage across all markets remain not
confirmed.

## `scripts/check_provider_router.py`

**Purpose:** P1B.1 config + wiring sanity check for `ProviderRouter`
(`aegis/data/provider_router.py`). Prints the route table from
`config/providers.yaml`, validates every configured symbol/index-code
mapping (`aegis/data/symbol_mapping.py`), and reports whether the
`tushare`/`yfinance` packages are installed — all without attempting any
live provider call and without ever reading or printing a token value.
Introduced P1B.1.

**Example:**

```bash
python scripts/check_provider_router.py
python scripts/check_provider_router.py --config config/providers.yaml --output data/processed/provider_diagnostics/provider_router_report.json
```

**Inputs:**

```text
usage: check_provider_router.py [-h] [--config CONFIG] [--output OUTPUT]

--config CONFIG   default: config/providers.yaml
--output OUTPUT   default: data/processed/provider_diagnostics/provider_router_report.json
```

**Outputs:** A `provider_router_report.json` at `--output` with:
`route_table` (flat list of `{data_type, market, provider}`),
`route_checks` (per-pair status — `"not_configured"`/`"unsupported"` when
the config says so, otherwise `"skipped"` this round, each with an
explicit `reason`), `mapping_checks` (every configured symbol/index
mapping, whether it resolved to the expected value), and
`package_availability` (`{"tushare": bool, "yfinance": bool}`).

**Failure behavior:** A missing/unreadable config file is a controlled
error (printed to stderr, exit 1, never a raw traceback). Every
configured route is reported `"skipped"` (not attempted) rather than
crashing — this script deliberately does not attempt any live provider
call this round; see `docs/P1B1_PROVIDER_ROUTER_RESULT.md`'s "Known
gaps". Never touches `os.environ`/`.env`/any token value.

## `scripts/validate_provider_router_live.py`

**Purpose:** P1B.2 live validation for `ProviderRouter`'s H/US
**secondary** (`yahoo_finance`) route only — daily bars, index bars, and
a `stock_basic` not_configured/unsupported check. Deliberately never
constructs a `TushareAdapter`, never reads `.env`/`os.environ`, never
requires `TUSHARE_TOKEN`. Complements (does not replace)
`check_provider_router.py` (config/wiring only, no live call) and
`validate_real_data.py` (Tushare/A股 only). Introduced P1B.2.

**Example:**

```bash
python scripts/validate_provider_router_live.py
python scripts/validate_provider_router_live.py --start 2026-06-01 --end 2026-07-03
python scripts/validate_provider_router_live.py --markets H,US
python scripts/validate_provider_router_live.py --output data/processed/provider_router/provider_router_live_report.json
```

**Inputs:**

```text
usage: validate_provider_router_live.py [-h] [--start START] [--end END]
                                        [--markets MARKETS] [--config CONFIG]
                                        [--output OUTPUT]

--start START       YYYY-MM-DD (informational; the router/adapter call
                    currently uses a fixed recent 30-day window internally)
--end END           YYYY-MM-DD
--markets MARKETS   Comma-separated; only H,US accepted (default: H,US) —
                    A股/Tushare is out of scope for this script
--config CONFIG     default: config/providers.yaml
--output OUTPUT     default: data/processed/provider_router/provider_router_live_report.json
```

**Outputs:** A report JSON at `--output` — `run_id`, `created_at`,
`network_attempted`, one `checks[]` entry per
`{h,us}_{daily_bars,index_bars,stock_basic}`
(`check_name`/`market`/`data_type`/`provider`/`sample_symbol`/
`mapped_symbol`/`status`/`rows_returned`/`warning`/`error_type`), and a
`summary` with per-status counts (`pass_count` through
`unsupported_count`).

**Status vocabulary:** `pass`, `fail`, `unknown` (call succeeded, zero
rows — never reads as `pass`), `skipped`, `not_configured`,
`dependency_missing` (detected via `YahooFinanceAdapter.is_configured()`
*before* any call is attempted — never guessed from an exception
message), `network_unavailable` (a `ProviderError` whose message looks
connection/DNS/proxy/timeout related), `unsupported`.

**Failure behavior:** An unknown `--markets` value (anything other than
H/US) is a controlled argument error, exit 1, never a raw traceback. A
missing `yfinance` package or unreachable network never crashes the
run — every check degrades to `dependency_missing`/`network_unavailable`/
`unknown` and a report is still written. **Exits 0 if at least one H/US
daily/index route reports `pass`; exits 1 otherwise** (a
`stock_basic` `not_configured` result never affects the exit code — it
is the expected, structural state). Verified this Cowork sandbox run:
`yfinance` not installed → every daily/index check `dependency_missing`,
both `stock_basic` checks `not_configured`, exit 1, valid report still
written. Full findings: `docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md`.

## `scripts/run_market_snapshot_smoke.py`

**Purpose:** P1B.4 smoke run proving the already-implemented
MarketSnapshot layer (`MarketSnapshotService` + `MarketRegimeAnalyzer`,
Phase 2) can actually consume H/US daily/index bars through
`MarketDataService` + `ProviderRouter`'s `yahoo_finance` route
(confirmed real per P1B.2, wired per P1B.3) and produce honest
`MarketSnapshot` output for H and US. Scoped to H/US only — deliberately
never constructs a `TushareAdapter`, never reads `.env`/`TUSHARE_TOKEN`.
Does not touch UniverseBuilder/Signal Library/Expert Agents/Decision
Engine/Recommendation/Paper Trading/Dashboard. Introduced P1B.4.

**Example:**

```bash
python scripts/run_market_snapshot_smoke.py --date 2026-07-04
python scripts/run_market_snapshot_smoke.py --date 2026-07-04 --markets H,US
```

**Inputs:**

```text
usage: run_market_snapshot_smoke.py [-h] --date DATE [--markets MARKETS]
                                     [--config CONFIG] [--output OUTPUT]
                                     [--gaps-path GAPS_PATH]

--date DATE           YYYY-MM-DD (required)
--markets MARKETS     Comma-separated; only H,US accepted (default: H,US) —
                      A股 already has its own proven Tushare-first pipeline
                      via run_pre_market.py, out of scope here
--config CONFIG       default: config/providers.yaml
--output OUTPUT       default: data/processed/market_snapshot_smoke/market_snapshot_smoke_report.json
--gaps-path GAPS_PATH default: data/records/data_gaps.jsonl (the same shared
                      DataGap log every other pipeline script writes to)
```

**P1D caution:** since P1C.3, the default `--output` path
(`data/processed/market_snapshot_smoke/market_snapshot_smoke_report.json`)
is no longer a disposable sandbox artifact — it holds the user's real,
locally-confirmed H/US `pass` result, which the desktop page's/
gateway's H/US `confirmed_live` coverage is built on. Running this
command from a sandbox with no `yfinance` (like this Cowork sandbox)
**will overwrite that real result** with a degraded
`dependency_missing` report. Treat this file with the same
"do not overwrite from this sandbox" caution as
`provider_router_live_report.json`: either rely on the existing report
instead of re-running this command, or pass an explicit disposable
`--output` path first. If it is overwritten, the stock-agent workspace
mirror
(`~/.openclaw/agents/stock-agent/workspace/project-aegis/market_snapshot_smoke_report.json`,
refreshed by `scripts/refresh_stock_agent_aegis_status.py`) is a
reliable restore point — this is exactly how the P1D round's
accidental overwrite was recovered. See
`docs/P1D_REAL_PREMARKET_PIPELINE_SMOKE_RESULT.md`.

**Outputs:** A report JSON at `--output` — `run_id`, `created_at`,
`date`, `markets`, one `results[market]` entry per requested market
(`primary_index_internal_code`, `index_bars_provider_route`/
`rows_returned`/`status`, `daily_bars_sample_symbol`/`provider_route`/
`rows_returned`/`status`, the full produced `market_snapshot` object, and
an `overall_status`), and a `summary` with per-status counts.

**No future data:** every bars DataFrame `MarketDataService` returns is
filtered (by a script-local `MarketDataService` subclass —
`aegis/market/service.py` itself is unmodified) to rows with
`trade_date <= --date` before `MarketSnapshotService`/
`MarketRegimeAnalyzer` ever see it. Any dropped row is recorded as an
info-level DataGap (`provider: "market_snapshot_smoke"`), never silently
discarded.

**Status vocabulary (`overall_status`/`index_bars_status`/
`daily_bars_status`):** `pass` (real, usable bars — P1B.4.1: derived from
`_bars_are_usable()`, the same non-empty + `"close"`-column +
minimum-bar-count check `MarketRegimeAnalyzer` itself applies, not a raw
row count), `partial` (usable bars, but `MarketRegimeAnalyzer` marked
`data_quality.status="partial"` — fewer than the full 20-day window),
`data_gap` (real rows but not usable — e.g. no `"close"` column, or below
the minimum bar count — or another otherwise-unclassified failure),
`dependency_missing` (the DataGap message names a missing package),
`network_unavailable` (the DataGap message looks connection/DNS/proxy/
timeout related), `unknown` (call succeeded but returned zero rows),
`skipped` (no sample configured for that market).

**P1B.4.1 — `route_snapshot_consistency` (new field, per market):**
`route_pass_snapshot_pass`, `route_pass_snapshot_partial`,
`route_fail_snapshot_unknown`, or an explicitly labeled
`inconsistent_route_pass_snapshot_data_gap`/
`inconsistent_route_fail_snapshot_has_data` state that should be
structurally impossible (proven by a dedicated regression test) but is
never silently reported as success if it somehow still occurs. See
`docs/P1B4_MARKETSNAPSHOT_SMOKE_CONSISTENCY_RESULT.md`.

**Failure behavior:** An unknown `--markets` value (anything other than
H/US) is a controlled argument error, exit 1, never a raw traceback. A
missing `yfinance` package or unreachable network never crashes the
run — `MarketSnapshot` still degrades to `trend_state="unknown"` per
Phase 2's existing rules, a route-specific DataGap
(`provider: "yahoo_finance"`) is recorded, and a valid report is still
written. **P1B.4.1: exits 0 only if *every* requested market reports
`pass`/`partial` and no market reports an `inconsistent_*` consistency
state; exits 1 otherwise** (previously: exit 0 if *any* requested market
passed/partial — changed to require all requested markets, per
`Claude_Cowork_P1B4_1_THEN_P1C_DESKTOP_READONLY.md`). Verified this
Cowork sandbox run: `yfinance` not installed → both H and US report
`dependency_missing`, `route_fail_snapshot_unknown`, exit 1, valid report
still written, `dashboard/index.html` byte-identical. Full findings:
`docs/P1B4_HUS_MARKETSNAPSHOT_SMOKE_RESULT.md` and
`docs/P1B4_MARKETSNAPSHOT_SMOKE_CONSISTENCY_RESULT.md`.

## `scripts/build_desktop_status.py`

**Purpose:** P1C read-only desktop status page builder, polished in
P1C.1. Reads only already-persisted records/report files
(`config/holdings.yaml`,
`data/records/{recommendations,paper_trades,reviews,data_gaps}.jsonl`,
the latest `provider_coverage_report.json`,
`provider_router_live_report.json`, and `market_snapshot_smoke_report.json`)
and renders `data/desktop/aegis_status.html` (plus a `aegis_status.json`
sidecar). Never fetches live data, never triggers a new smoke/validation
run itself, never fabricates P&L/recommendations/market status, and
never touches `dashboard/index.html` (a completely separate file/
pipeline). Introduced P1C; P1C.1 added the `--provider-coverage-report`
flag, A股 core/enhanced coverage detection, `translate="no"`/
`notranslate` HTML rendering, human-Chinese market/status labels, and
the current-vs-historical DataGap split.

**Example:**

```bash
python scripts/build_desktop_status.py
```

**Inputs:**

```text
usage: build_desktop_status.py [-h] [--holdings-path HOLDINGS_PATH]
                                [--records-dir RECORDS_DIR]
                                [--provider-coverage-report PATH]
                                [--provider-router-live-report PATH]
                                [--market-snapshot-smoke-report PATH]
                                [--output-html OUTPUT_HTML]
                                [--output-json OUTPUT_JSON]

--holdings-path                    default: config/holdings.yaml
--records-dir                      default: data/records
--provider-coverage-report         default: data/processed/provider_diagnostics/provider_coverage_report.json  (P1C.1)
--provider-router-live-report      default: data/processed/provider_router/provider_router_live_report.json
--market-snapshot-smoke-report     default: data/processed/market_snapshot_smoke/market_snapshot_smoke_report.json
--output-html                      default: data/desktop/aegis_status.html
--output-json                      default: data/desktop/aegis_status.json
```

**Outputs:** `data/desktop/aegis_status.html` (human-viewable, now
`translate="no"`/`notranslate`-protected with Chinese market/status
labels) and `data/desktop/aegis_status.json` (the same status dict,
machine-readable — raw enum values unchanged; the human-label mapping is
display-only — also the shared function `scripts/aegis_agent_gateway.py`'s
`status`/`summary`/`desktop-page` commands call directly, so the two
never drift apart).

**Failure behavior:** Any missing source file/record renders an honest
`"no_data"` state in the relevant section — never a crash, never a
fabricated value. A malformed report JSON is treated the same as a
missing one. Never reads `.env`/any token — this script never imports a
provider adapter at all.

## `scripts/aegis_agent_gateway.py`

**Purpose:** P1C read-only agent gateway — the single approved entry
point for an external agent (OpenClaw, Feishu, or any future
automation) to query Project Aegis. See
`docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md` and
`docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md` for the full contract.
Introduced P1C; P1C.1 added `--provider-coverage-report` and changed
`desktop-page`'s return shape (see below).

**Example:**

```bash
python scripts/aegis_agent_gateway.py status
python scripts/aegis_agent_gateway.py holdings
python scripts/aegis_agent_gateway.py summary
python scripts/aegis_agent_gateway.py desktop-page
python scripts/aegis_agent_gateway.py buy   # refused, exit 1
```

**Inputs:**

```text
usage: aegis_agent_gateway.py [-h] [--holdings-path HOLDINGS_PATH]
                               [--records-dir RECORDS_DIR]
                               [--provider-coverage-report PATH]
                               [--provider-router-live-report PATH]
                               [--market-snapshot-smoke-report PATH]
                               [--provider-diagnostics-report PATH]
                               [--output-html OUTPUT_HTML]
                               [--output-json OUTPUT_JSON]
                               command

Allowed commands: status, holdings, recommendations, paper-summary,
review-summary, provider-report, provider-router-report,
market-snapshot-smoke, data-gaps, desktop-page, summary.

Forbidden commands (refused, never executed): buy, sell, trade, order,
broker, auto-trade, rebalance, paper-buy, paper-sell,
create-paper-trade, modify-decision, modify-recommendation.
```

**Outputs:** JSON on stdout. Success (every command except
`desktop-page`): `{"ok": true, "command": ..., "data": ...}`, exit 0.

**`desktop-page` (P1C.1 — flat shape, deliberate breaking change):**
`{"ok": true, "path": "data/desktop/aegis_status.html", "absolute_path":
"...", "open_command": "open data/desktop/aegis_status.html"}`, exit 0.
No `"command"`/`"data"` wrapper — an OpenClaw/Feishu adapter can read
`path`/`open_command` directly without unwrapping anything.

Refusal: `{"ok": false, "error": "forbidden_command", "command": ...,
"message": ...}`, exit 1. Unknown command: `{"ok": false, "error":
"unknown_command", ...}`, exit 1.

**Failure behavior:** Never raises — every failure mode above is a
structured JSON result with a deterministic exit code. Never creates a
`PaperTrade`, never calls a broker (none exists in this repo), never
mutates a Decision/Recommendation record, never reads `.env`/any token
(this script never imports a provider adapter), never special-cases
CRCL.

## `scripts/openclaw_aegis_readonly.py`

**Purpose:** P1C.1 OpenClaw/Feishu text-command adapter. Translates a
raw chat-message string of the form `"aegis <command>"` (e.g. `"aegis
status"`) into a call to `scripts.aegis_agent_gateway.dispatch()`. Has
**no allow/forbid logic of its own** — every command, allowed or
forbidden, is decided entirely by the gateway; this adapter cannot grant
a capability the gateway doesn't already have. Never talks to Feishu or
OpenClaw itself (no credentials, no network, no message-sending). See
`docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md` for the full contract.

**Example:**

```bash
python scripts/openclaw_aegis_readonly.py "aegis status"
python scripts/openclaw_aegis_readonly.py "aegis holdings"
python scripts/openclaw_aegis_readonly.py "aegis desktop-page"
python scripts/openclaw_aegis_readonly.py "aegis buy"   # refused, exit 1
```

**Inputs:** A single positional text argument (or several unquoted
words, joined) matching `"aegis <command>"` case-insensitively; extra
whitespace tolerated. Missing the `"aegis "` prefix or no argument at
all is a controlled input error, never a best-effort guess.

**Outputs:** Whatever `scripts/aegis_agent_gateway.py`'s `dispatch()`
returns for the parsed command (same JSON shapes as above), printed to
stdout with the same exit code. On a malformed command string:
`{"ok": false, "error": "invalid_command_text", "message": ...}`, exit
1. On no input at all: `{"ok": false, "error":
"missing_command_text", "message": ...}`, exit 1.

**Failure behavior:** Never raises on malformed input — always a
controlled JSON error. Never reads `.env`/any token (imports neither a
provider adapter nor `os.environ`/`dotenv`), never creates a
`PaperTrade`, never calls a broker, never special-cases CRCL.

## `scripts/check_openclaw_aegis_readonly.py`

**Purpose:** P1C.2 local, credential-free verification of the OpenClaw/
Feishu read-only adapter. Requires no Feishu credentials, no `openclaw`
install, and no network access — it only shells out to
`scripts/openclaw_aegis_readonly.py` the same way a real OpenClaw/Feishu
channel would (one subprocess call per `"aegis <command>"` string). See
`docs/P1C2_OPENCLAW_FEISHU_READONLY_CONNECT_RESULT.md` for full results
and `docs/P1C2_OPENCLAW_FEISHU_SETUP_RUNBOOK.md` for how this fits into
an actual Feishu connection.

**Example:**

```bash
python scripts/check_openclaw_aegis_readonly.py
```

**Inputs:** No required arguments. Optional `--json-only` flag (kept for
explicit scripting use; the default output is already JSON-only).

**Checks performed:**
- `aegis status` / `aegis holdings` / `aegis summary` each return
  `{"ok": true, ...}` and exit 0;
- `aegis buy` is refused (`{"ok": false, "error": "forbidden_command",
  ...}`, non-zero exit);
- the forbidden command never creates or modifies
  `data/records/paper_trades.jsonl` — proven via a `(mtime, sha256)`
  file fingerprint taken immediately before and after the call, not
  just trusted from the JSON response;
- `dashboard/index.html` is byte-identical to the Vault-level copy —
  skipped honestly (never silently reported as pass) if that copy
  isn't present in the running environment.

**Outputs:** One JSON summary to stdout: `{"ok": <bool>, "checks":
{"status": {...}, "holdings": {...}, "summary": {...},
"buy_refused_no_paper_trade_write": {...}, "dashboard_unchanged":
{...}}}`. Exit 0 if every check passed, exit 1 otherwise.

**Failure behavior:** Never raises — a subprocess timeout, a non-JSON
response, or a missing file all degrade to an honest `"passed": false`
in the relevant check, never a crash. Never reads `.env`/any token
(imports neither a provider adapter nor `os.environ`/`dotenv`), never
writes to `data/records/` itself, never creates a `PaperTrade`, never
calls a broker, never special-cases CRCL.

## `scripts/aegis_openclaw_command.sh` (optional)

**Purpose:** P1C.2 tiny bash wrapper around
`scripts/openclaw_aegis_readonly.py`, so an OpenClaw/Feishu integration
can invoke one short, stable shell command instead of a full `python
scripts/openclaw_aegis_readonly.py "..."` invocation. No logic of its
own: no allow/forbid decisions, no secrets, no write operations.

**Example:**

```bash
./scripts/aegis_openclaw_command.sh aegis status
./scripts/aegis_openclaw_command.sh aegis buy   # refused, exit 1
```

**Inputs/Outputs/Failure behavior:** Identical to
`scripts/openclaw_aegis_readonly.py` — this wrapper joins its arguments
into one string and execs the Python adapter directly, passing the exit
code and stdout straight through.

## `scripts/refresh_stock_agent_aegis_status.py`

**Purpose:** P1C.3 read-only helper that keeps the Feishu/OpenClaw
stock-agent's on-disk Project Aegis status mirror fresh, so its read
flow stays strictly file-based — no `exec`, no `nodes.invoke`, no
localhost `web_fetch` dependency. Calls the same
`build_desktop_status.build_status()`/`render_html()` functions the
desktop page and gateway already use (no second, divergent status
implementation), then mirrors a fixed set of already-persisted files
into `~/.openclaw/agents/stock-agent/workspace/project-aegis/`.

**Example:**

```bash
python scripts/refresh_stock_agent_aegis_status.py
```

**Inputs:** All optional, mirroring `build_desktop_status.py`'s flags:
`--holdings-path`, `--records-dir`, `--output-html`, `--output-json`,
`--provider-coverage-report`, `--provider-router-live-report`,
`--market-snapshot-smoke-report`, `--stock-agent-workspace` (default:
`~/.openclaw/agents/stock-agent/workspace/project-aegis/`).

**What it does, in order:**
1. Rebuilds `data/desktop/aegis_status.json`/`.html`.
2. Creates the stock-agent workspace directory if missing.
3. Copies `aegis_status.json`/`.html` plus (only if each already exists
   on disk) `market_snapshot_smoke_report.json`,
   `provider_router_live_report.json`, `provider_coverage_report.json`
   into that directory.
4. Writes `README_FOR_STOCK_AGENT.md` into the same directory, restating
   the read-only rules (no PaperTrade, no broker, no CRCL
   special-casing, don't edit these files directly).
5. Prints every file copied and the final target directory path.

**Outputs:** Console lines listing each copied file and the target
directory; the mirrored files themselves in the stock-agent workspace.

**Failure behavior:** Never reads `.env`/any token, never touches
`data/records/paper_trades.jsonl`, never calls a broker or constructs a
`PaperTrade`, never modifies `dashboard/index.html`, never special-cases
CRCL. A missing *optional* report file is skipped silently (listed in
the printed "Skipped" section), never an error.

## `scripts/serve_desktop.py` (optional)

**Purpose:** Serves `data/desktop/` (the page built by
`build_desktop_status.py`) over plain HTTP for local viewing only.
Introduced P1C.

**Example:**

```bash
python scripts/serve_desktop.py
python scripts/serve_desktop.py --host 127.0.0.1 --port 8766
```

**Inputs:**

```text
usage: serve_desktop.py [-h] [--host HOST] [--port PORT] [--serve-dir SERVE_DIR]

--host HOST           must be 127.0.0.1 (or localhost) — enforced, exit 1 otherwise
--port PORT           default: 8765
--serve-dir SERVE_DIR default: data/desktop
```

**Outputs:** None (serves files in place); prints the URL to stdout.

**Failure behavior:** A non-loopback `--host` is a controlled argument
error, exit 1 — never binds beyond `127.0.0.1`. Directory listing is
disabled (`403`) — only files that actually exist under `data/desktop/`
are servable. If the port is already in use, prints the exact `lsof`/
`kill` guidance (or "use a different `--port`") to stderr and exits 1
rather than crashing with a raw traceback.

## Not implemented

The following are referenced by the Master Spec's later-phase roadmap but
do not exist in the current P0 codebase, and were not created in Phase 8
(Phase 8 is documentation-only unless a script already exists):

- `scripts/init_project.py` — not implemented in current P0 codebase.
- `scripts/run_daily.py` — not implemented in current P0 codebase.
- `scripts/run_midday.py` — not implemented in current P0 codebase.

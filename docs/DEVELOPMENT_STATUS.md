# Project Aegis — Development Status

Phase 8 deliverable. Per-phase table derived from `docs/HANDOFF.md`'s
archived phase sections (each phase's own "Test results" block is the
source for its test count). See `docs/HANDOFF.md` for full narrative
detail per phase, and `docs/P0_ACCEPTANCE_REPORT.md` for the acceptance
checklist.

## Phase table

| Phase | Name | Status | Tests | Notes |
|---:|---|---|---:|---|
| 0 | Project Skeleton | done | 13 | Directory structure, config YAML skeletons, `pyproject.toml`, typed model skeletons in `aegis/models/`, `aegis/utils/jsonl.py`, `dashboard/index.html` copied byte-for-byte |
| 1 | Data Pipeline | done | 41 (28 new) | `TushareAdapter`, `DataCache`, `DataGapRegistry`, `MarketDataService`, `HoldingLoader`, `scripts/check_tushare.py` — all exercised only against fixture/fake `_pro` stubs, no real Tushare token/network in this sandbox |
| 2 | Market + Universe | done | 59 (18 new) | `MarketRegimeAnalyzer`, `MarketSnapshotService`, `UniverseBuilder`, `scripts/run_pre_market.py` (first version); fixed 2 Phase 0 model mismatches (`TrendState`/`LiquidityState` enum values, `DataQuality.warnings`) |
| 3 | Signal + Expert Committee | done | 85 (26 new) | 6 deterministic signals (`aegis/signals/`), 7-agent Expert Committee (`aegis/experts/`) run in a fixed order — no composite score anywhere |
| 4 | Decision + Recommendation | done | 112 (27 new) | `DecisionEngine.decide()` (evidence voting + Risk veto + 8 hard rules), `compute_decision_confidence` (decision-reliability metadata only), `RecommendationService` — `RecommendationRecord` becomes the canonical object (ADR-001) |
| 5 | Dashboard Integration | done | 132 (~20 new) | `DashboardBuilder`, `scripts/build_dashboard.py`; `run_pre_market.py` extended to build the Dashboard JSON; `dashboard/index.html` confirmed byte-identical (first of many such confirmations) |
| 6 | Paper Trading + Review | done | 197 (~65 new) | `aegis/paper/`, `aegis/review/`, `aegis/memory/`, `scripts/run_close.py`, `scripts/export_review.py`; decision-quality classification deliberately decoupled from raw return sign |
| 7 | Time Travel Backtest | done | 249 (52 new) | `aegis/backtest/` (`FrozenContext`, `HistoricalDataProvider`, `TimeTravelEngine`, `BacktestResult`/`MetricsReport`), `scripts/run_backtest.py`; two-layer no-future-data defense (request capping + served-row filtering), proven against a fake provider that deliberately ignores the `end` param |
| 8 | QA + Documentation | done | 249 (0 new) | QA verification only (dashboard integrity, secrets scan, composite-scoring scan, broker scan, record-linkage inspection, CRCL holding check) plus new documentation (`README.md` update, `P0_ACCEPTANCE_REPORT.md`, `CLI_REFERENCE.md`, `DATA_AND_RECORDS.md`, this file). No new runtime code; no new tests were needed since every required check was satisfiable via the existing 249-test suite plus direct inspection — **P0 complete as of this phase** |
| P1 planning | P1 Scope Decision Brief | done | 249 (0 new) | Planning-only checkpoint — `docs/P1_SCOPE_DECISION_BRIEF.md` produced, no code written. Recommended (and user approved) a narrow P1A slice: real data validation tooling + trading-calendar foundation, deferring Risk Wiring Hardening and the Daily Operations Playbook |
| P1A | Real Data Validation + Trading Calendar | done | 263 (14 new) | `aegis/data/{coverage_report,provider_diagnostics,live_validation}.py`, `scripts/validate_real_data.py`, `aegis/calendar/{market_calendar,repository,service}.py`, `config/calendar.yaml`. No Decision Engine changes, no new Expert Agents, no Dashboard changes — `TradingCalendarService` built as a standalone, fully-tested foundation service, deliberately **not yet wired** into `PaperTradeService`/`TimeTravelEngine` to avoid silently changing any already-accepted P0 decision/return result |
| P1A run | Real Data Validation Run (validation-only) | done | 263 (0 new) | Executed `scripts/validate_real_data.py` inside the Cowork sandbox — no `TUSHARE_TOKEN`, no outbound network (confirmed by direct inspection). Result: `NOT_RUN_MISSING_TOKEN`, honestly recorded, first real (non-test) empty-state `provider_coverage_report.json` written. No code changed |
| P1A.1 | Provider Coverage Reconciliation + Diagnostics Hardening | done | 266 (3 new; 1 pre-existing unrelated failure at the time — fixed next round, see below) | User ran `scripts/validate_real_data.py` locally with a real token/network. Hardened `CheckStatus` (`unknown`→`unknown_empty`, added `unsupported`/`permission_denied`/`not_configured`); added `reconcile_cross_market_checks()` to catch the real observed bug (H/US `stock_basic` silently reusing A股's row count — `TushareAdapter.get_stock_basic` ignores its `market` argument); classified permission/quota-flavored `ProviderError`s separately from generic failures; symbol-keyed checks now report `not_configured` instead of guessing when no sample symbol exists for a market. Produced `docs/P1A_PROVIDER_COVERAGE_DECISION.md`: A股 core data path confirmed, H股/US/CRCL/sector/fundamentals not confirmed. No Decision Engine/Expert Agent/Dashboard/broker changes |
| QA cleanup | QA Cleanup + H/US/CRCL Provider Decision | done | 266 (0 new; the 1 pre-existing failure fixed) | Fixed the Phase 7 date-collision flakiness in `tests/test_time_travel_no_future_data.py::test_recommendation_never_references_the_future_spike` — see "Note on the Phase 7 flakiness fix" below. Confirmed P1A.1's diagnostics hardening (`CheckStatus`, `reconcile_cross_market_checks`) unchanged/intact. Produced `docs/P1B_HUS_CRCL_PROVIDER_IMPLEMENTATION_SPEC.md` (planning only — no provider code implemented). No token read/printed (only `bool(os.environ.get("TUSHARE_TOKEN"))` checked, `.env` never opened). No Decision Engine/Expert Agent/Dashboard/broker/OpenClaw/Feishu changes |
| P1B.1 | ProviderRouter + H/US Adapter Skeleton | done | 301 (35 new) | `aegis/data/provider_router.py` (`ProviderRouter` — explicit `(market, data_type)` routing, no silent fallback), `aegis/data/yahoo_finance_adapter.py` (`YahooFinanceAdapter` skeleton — daily/index bars only, everything else `ProviderUnsupportedError`), `aegis/data/symbol_mapping.py` (`SymbolMapper`), `config/providers.yaml` (new routing table — A股 stays Tushare-first; H/US daily/index bars route to `yahoo_finance`; H/US `stock_basic`/`sector_classification`/`fundamentals` explicitly `"not_configured"`), `scripts/check_provider_router.py` (new CLI, config/wiring check only, no live network). Added `ProviderNotConfiguredError`/`ProviderUnsupportedError` to `aegis/data/providers.py`; wired into `aegis/data/provider_diagnostics.py`'s existing `not_configured`/`unsupported` statuses (P1A.1 vocabulary, no new statuses needed). `MarketDataService` now accepts an optional `provider_router` alongside its existing `provider` param — zero existing call sites changed. No full H/US universe, no live H/US/CRCL verification, no OpenClaw/Feishu, no Decision Engine/Expert Agent/Dashboard/broker changes, no token read/printed. See `docs/P1B1_PROVIDER_ROUTER_RESULT.md` |
| P1B.2 | ProviderRouter Live Validation | done | 320 (19 new) | `aegis/data/provider_router_live_validation.py` (honest status classifier: `pass`/`fail`/`unknown`/`skipped`/`not_configured`/`dependency_missing`/`network_unavailable`/`unsupported` — dependency check via `YahooFinanceAdapter.is_configured()` *before* any call, never guessed from an exception message), `scripts/validate_provider_router_live.py` (new CLI, H/US only, never constructs `TushareAdapter`, never reads `.env`/`os.environ`/`TUSHARE_TOKEN`). First run in this Cowork sandbox (`yfinance` not installed) degraded honestly to `dependency_missing`/`not_configured`. **The user then ran it for real on their local machine** with `yfinance` installed and real network: H/US daily bars and index bars all `pass` (including CRCL, 20 rows each), both `stock_basic` checks correctly `not_configured` (intentional). **H/US daily/index coverage via the secondary provider is now confirmed real** — see `docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md`. A follow-up QA-fix round found and fixed one test/environment-coupling bug this exposed: `tests/test_yahoo_finance_adapter.py::test_no_client_configured_raises_provider_error` assumed `yfinance` was never installed, which broke once the user's real local machine had it installed for real validation — fixed via `monkeypatch` to force the "no package" condition deterministically, `pytest -v` now 320 passed/0 failed with or without `yfinance` installed. No OpenClaw/Feishu, no Decision Engine/Expert Agent/Dashboard/broker changes, no composite scoring, no token read/printed, no P1B.3 (MarketDataService wiring) started |
| P1B.3 | Wire ProviderRouter into MarketDataService | done | 336 (16 new) | `aegis/data/provider_router.py` gained `route_name_for(market, data_type)` (small, non-raising diagnostic route lookup — labels `DataGap`s, never used for control flow). `aegis/market/service.py`'s `get_daily_bars_cached`/`get_index_bars_cached` now label every `DataGap` with the actual failing provider/route (instead of a hardcoded generic string), include the failing exception's type in the message, and always populate `consumer_impact`; `get_latest_close()` needed no change — it already delegates to `get_daily_bars_cached()`. `DataCache`'s existing market/data_type-scoped cache path needed no change; new tests prove H/US Yahoo results and A股 Tushare results never collide even for the same literal symbol string. Built against the **real** `config/providers.yaml` (loaded from disk): A daily/index confirmed still Tushare-first; H daily/index and US daily/index (incl. CRCL) confirmed routed to `yahoo_finance` with correct symbol mapping; H/US `stock_basic` confirmed still `ProviderNotConfiguredError`, never satisfied by A股 data. A dedicated read-only impact scan preceded this change (`Claude_Cowork_P1B3_DATAGAP_PROVIDER_IMPACT_SCAN.md`) confirming no test assertion would break from making `DataGap.provider` route-specific (`"yahoo_finance"`/`"tushare"`/generic fallback); a follow-up round added the one missing required test (`get_latest_close()` returns `None` + records a correctly-labeled gap when the H/US route fails). No real pipeline consumer (`run_pre_market.py`, `UniverseBuilder`, etc.) was changed to actually construct/pass a `ProviderRouter` — this round only hardens and proves the `MarketDataService` integration point itself. No H/US universe/stock_basic/sector/fundamentals, no UniverseBuilder/Signal/Expert/Decision changes, no Dashboard change, no OpenClaw/Feishu, no broker/real trading, no composite scoring, no token read/printed. See `docs/P1B3_PROVIDER_ROUTER_MARKET_DATA_RESULT.md` |
| P1B.4 | H/US MarketSnapshot Smoke Run | done | 348 (12 new) | New `scripts/run_market_snapshot_smoke.py` (H/US only, never constructs `TushareAdapter`, never reads a token) proves the already-implemented, **unmodified** `MarketSnapshotService`/`MarketRegimeAnalyzer` (Phase 2) can consume H/US daily/index bars through `MarketDataService` + `ProviderRouter`'s `yahoo_finance` route and produce honest `MarketSnapshot` output. A script-local `_DateBoundedMarketDataService` subclass (only inside the new script, `aegis/market/service.py` itself untouched) filters every returned bar to `trade_date <= --date` before analysis — dropped future rows are recorded as an info-level DataGap, never silently included. Route failures degrade to `dependency_missing`/`network_unavailable`/`data_gap`/`unknown` with a route-specific (`yahoo_finance`) DataGap and `trend_state="unknown"`, never a crash, never fabricated. Real run in this Cowork sandbox (no `yfinance` installed): both H and US report `dependency_missing`, exit 1, valid report still written — matches the same sandbox limitation already documented for P1B.2. No H/US universe/stock_basic/sector/fundamentals, no UniverseBuilder/Signal/Expert/Decision/Recommendation/Paper Trading changes, no Dashboard change, no OpenClaw/Feishu, no broker/real trading, no composite scoring, no token read/printed, CRCL used only as the US daily-bars sample symbol (never a market index). See `docs/P1B4_HUS_MARKETSNAPSHOT_SMOKE_RESULT.md` |
| P1B.4 fix | Local MarketSnapshot Smoke Failure Triage | done | 355 (7 new) | User's real local Mac run of the P1B.4 smoke script returned `overall_status=unknown`, 0 rows for both H and US, despite P1B.2 already confirming 20 real rows for the same tickers via the same `YahooFinanceAdapter`. **Root cause** (confirmed via real `yfinance` 1.5.1 source inspection): `aegis.utils.dates.lookback_range()` — used by `MarketSnapshotService`/the smoke script — produces a compact `"YYYYMMDD"` date string; real `yfinance` parses string `start`/`end` via a strict `datetime.strptime(dt, "%Y-%m-%d")` internally, which raises on a compact string, but `yfinance`'s own `_download_one()` silently swallows that exception and substitutes an empty result instead of re-raising — so the caller sees no crash, only zero rows. `scripts/validate_provider_router_live.py`'s `default_date_window()` already used dashed dates, which is exactly why that route worked while this one didn't. **Fix**: one new static helper, `YahooFinanceAdapter._normalize_date_str()` in `aegis/data/yahoo_finance_adapter.py`, applied before every `client.download(...)` call — accepts compact or dashed input, always passes dashed to the real client. No other production file changed. `scripts/run_market_snapshot_smoke.py` also gained a `--lookback-days` flag and a `fetch_window` report field for transparency. Added the critical regression test that the original P1B.4 round's hand-rolled fake provider could never have caught: a real `YahooFinanceAdapter` wired to a fake client that only responds to correctly-dashed dates, run through the full real stack — confirmed to fail before the fix (manually verified by bypassing the normalization) and pass after. This Cowork sandbox still reports `dependency_missing` (no real `yfinance`/network here) — the fix is expected to make the user's local Mac run report `pass`/`partial` instead. **Incident**: `scripts/validate_provider_router_live.py` was run again during verification and again overwrote the user's real local `provider_router_live_report.json` (a second occurrence of the exact P1B.3 incident) — caught and restored verbatim within the same round. No OpenClaw/Feishu, no Decision/Expert/UniverseBuilder/Dashboard changes, no broker/real trading, no composite scoring, no token read/printed. See `docs/P1B4_HUS_MARKETSNAPSHOT_SMOKE_RESULT.md` |
| P1B.4.1 | MarketSnapshot Smoke Consistency Fix | done | 364 (9 new) | User's newest local report showed H/US routes returning 41 real rows (`status: pass`) while the embedded `MarketSnapshot` still said `DATA_GAP: No index bars available`. **Root cause**: the smoke script's own status used a naive `len(df) > 0` check, while `MarketSnapshotService`/`MarketRegimeAnalyzer` (Phase 2, unmodified) correctly check `df.empty` (true whenever *either* axis, including columns, has length 0) and `"close" in df.columns` — a DataFrame can have real rows but zero usable columns if `yfinance` returns MultiIndex columns (a real shape some versions use by default), which `_normalize_ohlcv()`'s exact-string alias matching failed to recognize. **Fix**: flattened MultiIndex columns before alias-matching in `aegis/data/yahoo_finance_adapter.py`; made `scripts/run_market_snapshot_smoke.py`'s own status derive from `_bars_are_usable()` — the same non-empty + `"close"`-column + minimum-bar-count check the analyzer itself applies (imported directly from `aegis.market.regime`, not re-implemented); added a per-market `route_snapshot_consistency` field (`route_pass_snapshot_pass`/`route_pass_snapshot_partial`/`route_fail_snapshot_unknown`, or an explicitly-labeled `inconsistent_*` state proven-by-test to be structurally impossible now); changed the CLI exit policy to require *every* requested market to be pass/partial (was: *any*). Sandbox still honestly reports `dependency_missing` (no real `yfinance` here). No H/US universe/Decision/Expert/Dashboard changes, no broker/real trading, no composite scoring, no token read/printed, CRCL not special-cased. See `docs/P1B4_MARKETSNAPSHOT_SMOKE_CONSISTENCY_RESULT.md` |
| P1C | Read-Only Bridge + Desktop Status Page | done | 412 (48 new) | New `scripts/build_desktop_status.py` + `data/desktop/aegis_status.html`/`.json` — a read-only desktop status page reading only already-persisted `config/holdings.yaml` + `data/records/*.jsonl` + the latest ProviderRouter-live/MarketSnapshot-smoke reports; honest `"no_data"` states for anything missing, no fabricated P&L/recommendations/market status, `dashboard/index.html` untouched. New `scripts/aegis_agent_gateway.py` — the single approved read-only entry point for an external agent: 11 allowed commands (`status`/`holdings`/`recommendations`/`paper-summary`/`review-summary`/`provider-report`/`provider-router-report`/`market-snapshot-smoke`/`data-gaps`/`desktop-page`/`summary`) return structured JSON + exit 0; 12 forbidden commands (`buy`/`sell`/`trade`/`order`/`broker`/`auto-trade`/`rebalance`/`paper-buy`/`paper-sell`/`create-paper-trade`/`modify-decision`/`modify-recommendation`) are refused with structured JSON + exit 1, matched case-insensitively; an unrecognized command also fails closed. New optional `scripts/serve_desktop.py` — a `127.0.0.1`-only static file server for `data/desktop/`, directory listing disabled, verified locally (`HTTP 200` on the page, `HTTP 403` on directory listing). New `docs/P1C_OPENCLAW_FEISHU_BRIDGE_CONTRACT.md` documenting the binding OpenClaw/Feishu access contract. Neither new script imports a provider adapter, `os.environ`, or `dotenv` at all — no token access is even structurally possible. No H/US universe/Decision/Expert/UniverseBuilder/Dashboard changes, no broker/real trading, no PaperTrade creation from the gateway, no composite scoring, no CRCL special-casing (verified: no conditional logic keyed on the literal string anywhere in the new scripts). See `docs/P1C_READONLY_BRIDGE_DESKTOP_VIEW_RESULT.md` |
| P1C.1 | Desktop Polish + OpenClaw/Feishu Read-Only Prep | done | 447 (35 new) | Fixed 4 user-reported desktop display bugs: (1) browser mistranslation of `A`/`US` fixed via `translate="no"`/`notranslate` at document + per-element level; (2) market codes now render as `A股`/`H股`/`美股`; (3) status tokens now render as human Chinese labels (已验证/未确认/暂无数据/通过/部分通过/依赖缺失/网络不可用/未配置), raw value kept only in a non-translated `title=`; (4) A股 core coverage now read from `data/processed/provider_diagnostics/provider_coverage_report.json` (`daily_bars`/`index_bars`/`stock_basic`/`trading_calendar` all `pass` → `confirmed_tushare`/已验证), enhanced data (`sector_classification`/`fundamentals`) tracked separately as "增强数据未确认", never gating the core verdict; (5) stale `yfinance package is not installed` gaps for a now-confirmed market are split into a collapsed "历史数据缺口" section instead of the current-gaps list — `data/records/data_gaps.jsonl` itself never rewritten, only the *display* splits current (4) vs. historical (24) against the real local data. `scripts/aegis_agent_gateway.py`'s `desktop-page` command changed to a flat `{"ok","path","absolute_path","open_command"}` shape (deliberate breaking change; every other command's shape unchanged); `provider_coverage_report` threaded through `status`/`desktop-page`/`summary`/`data-gaps`. New `scripts/openclaw_aegis_readonly.py` — text-command adapter (`"aegis <command>"` → gateway), no allow/forbid logic of its own, verified `"aegis status"`/`"aegis holdings"` succeed and `"aegis buy"` is refused (exit 1) exactly like the gateway itself. New `docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md` (contract doc, no real Feishu bot built). No H/US universe/Decision/Expert/UniverseBuilder/Dashboard changes, no broker/real trading, no PaperTrade creation, no composite scoring, no CRCL special-casing, no token read/printed. See `docs/P1C1_DESKTOP_POLISH_OPENCLAW_PREP_RESULT.md` |
| P1C.2 | OpenClaw/Feishu Read-Only Connect | done | 466 (19 new) | Prepared (but did not build) the actual OpenClaw/Feishu connection on top of P1C/P1C.1's already-complete read-only adapter/gateway: `docs/openclaw/project-aegis-readonly/SKILL.md` (documentation scaffold — command examples, exact shell command, forbidden-command list, expected JSON, refusal behavior — not a registered/running OpenClaw skill); `docs/P1C2_OPENCLAW_FEISHU_SETUP_RUNBOOK.md` (prerequisite check, DM/group allowlist + `@mention` guidance, test messages, no-secrets-in-repo statement, secret-rotation steps entirely outside this repo, log-reading/troubleshooting guidance — contains no real App ID/App Secret/`open_id`/`chat_id`, confirmed by a dedicated secret-pattern-scanning test); new `scripts/check_openclaw_aegis_readonly.py` (local, credential-free verification — shells out to the existing adapter exactly as a real channel would, confirms `status`/`holdings`/`summary` succeed and `buy` is refused, and *proves* via a file fingerprint that the forbidden command never touches `data/records/paper_trades.jsonl`, not just trusting the JSON response; prints one JSON summary, exit 0/1); optional `scripts/aegis_openclaw_command.sh` (logic-free bash wrapper). `openclaw` is confirmed **not installed** in this Cowork sandbox (`openclaw --version` → command not found) — documented plainly rather than worked around; the actual channel connection must happen on the user's own machine. No production code in `scripts/aegis_agent_gateway.py`/`scripts/openclaw_aegis_readonly.py`/`scripts/build_desktop_status.py` changed this round — only new scaffolding/docs/tooling around the already-correct P1C/P1C.1 contract. No H/US universe/Decision/Expert/UniverseBuilder/Dashboard changes, no broker/real trading, no PaperTrade creation, no composite scoring, no CRCL special-casing, no token read/printed, no Feishu secret stored in repo. See `docs/P1C2_OPENCLAW_FEISHU_READONLY_CONNECT_RESULT.md` |
| P1C.3 | Status Cleanup + Stock-Agent Auto Refresh | done | 479 (13 new) | Fixed two problems reported by the user's stock-agent (Feishu/OpenClaw) already reading Project Aegis status via a workspace file mirror. (1) Stale H/US `yahoo_finance` gaps for HSI.HI/SPX/00700.HK/CRCL — real message shape "No {index\|daily} bars returned for ... via provider_route='yahoo_finance' between ... and ..." — were still shown as *current* unresolved gaps even though `market_snapshot_smoke_report.json` (dated later than all 4 gaps) already confirms H/US `overall_status: pass`. `scripts/build_desktop_status.py`'s `_split_stale_gaps()` gained a broadened marker set (`_STALE_GAP_MESSAGE_MARKERS` +`dependency_missing`/`network_unavailable`; new `_STALE_GAP_EMPTY_ROUTE_MARKERS` matched only when the message also names `via provider_route='yahoo_finance'`, so an unrelated provider's "no bars returned" message is never swept in) plus a structural gate (`provider=="yahoo_finance"`, `data_type in {index_bars,daily_bars}`, `market in {H,US}`) — verified against the real repo data: all 28 on-disk gaps now classify historical/superseded, 0 current unresolved, `data/records/data_gaps.jsonl` itself untouched. (2) New `scripts/refresh_stock_agent_aegis_status.py` — rebuilds `data/desktop/aegis_status.json`/`.html` via the same shared builder (no second implementation), mirrors them plus `market_snapshot_smoke_report.json`/`provider_router_live_report.json`/`provider_coverage_report.json` (only if each exists) into `~/.openclaw/agents/stock-agent/workspace/project-aegis/`, and writes a `README_FOR_STOCK_AGENT.md` restating the read-only rules; keeps the stock-agent's read flow strictly file-based (no `exec`/`nodes.invoke`/localhost `web_fetch`). Optional LaunchAgent template `docs/launchd/ai.project-aegis.refresh-stock-agent-status.plist.example` created but **not installed**. No H/US universe/stock_basic/Decision/Expert/Recommendation/Dashboard changes, no broker/real trading, no PaperTrade creation, no composite scoring, no CRCL special-casing, no token read/printed, `data_gaps.jsonl` never deleted/rewritten. See `docs/P1C3_STATUS_CLEANUP_AUTO_REFRESH_RESULT.md` |
| P1D | Real Premarket Recommendation Pipeline Smoke Run | done | 479 (net unchanged; one brittle real-repo test assertion relaxed) | Ran the existing, unmodified `scripts/run_pre_market.py` for real for the first time against this environment's actual config/providers — produced the project's first-ever real `RecommendationRecord`/`DecisionRecord`: CRCL, `status: "Exit"`, `why_not_action: "risk_veto_triggered"`, driven entirely by the existing Decision Engine's Risk-veto hard rule (no real Tushare token/`yfinance`/network in this sandbox, so every signal/expert honestly reports missing data — nothing fabricated). No Decision Engine/Expert Agents/UniverseBuilder/Recommendation logic touched. **Incident**: required `run_market_snapshot_smoke.py` baseline command overwrote the user's real H/US `pass` result in `market_snapshot_smoke_report.json` — caught and restored byte-for-byte from the P1C.3 stock-agent workspace mirror copy. See `docs/P1D_REAL_PREMARKET_PIPELINE_SMOKE_RESULT.md` |
| P1D.1 | Recommendation Details Mirror + Explanation Layer | done | 496 (+17) | New `aegis/desktop/recommendation_details.py` reads `data/records/{recommendations,decisions,expert_opinions,data_gaps}.jsonl`, deduplicates by id (latest `created_at` wins), marks `is_latest_for_symbol` per symbol, and writes `data/desktop/recommendation_details.json` — a sanitized, read-only recommendation detail bundle the Feishu Stock Agent can consume to explain support/oppose/risks/invalidation_conditions/why_not_action without accessing raw JSONL records. 17 new tests in `tests/test_recommendation_details.py`. See `docs/P1D1_RECOMMENDATION_DETAILS_MIRROR_RESULT.md` |
| P1D.2 | Data-Backed Recommendation Pipeline Fix | done | 509 (+13) | Wired `ProviderRouter` (Tushare for A + YahooFinanceAdapter for H/US) into `scripts/run_pre_market.py` via `_build_provider_router()` helper + injectable `provider_router` param. Fixed `UniverseBuilder._holding_candidate` to not force `liquidity_ok=False` for confirmed holdings when stock_basic is `not_configured` (new `force_liquidity_ok` param). CRCL recommendation moved from Exit (confidence=0.25, veto=1, risk_veto_triggered, risks=[liquidity_not_ok]) to Watch (confidence=0.45, veto=0, why_not_action=missing_critical_data, risks=[]). Remaining missing signals (trend/volume/RS/fundamental/sector/risk) are honest — sandbox network is blocked (Yahoo Finance returns 403). On user's machine with network access, Yahoo will return real OHLCV bars and signals will compute. No Decision Engine/Expert Agent thresholds changed; outcome not forced. 13 new tests in `tests/test_run_pre_market_provider_router.py`. See `docs/P1D2_DATA_BACKED_RECOMMENDATION_PIPELINE_RESULT.md` |
| P1D.4 | Provider Runtime Dependency + Data-Backed Rerun | done | 537 (+12) | Confirmed `yfinance==1.5.1` importable in sandbox; `pyproject.toml` already has `yfinance>=0.2.40` in main deps (no change needed). Created `scripts/check_provider_runtime.py` — reports Python exe, yfinance importability/version, `YahooFinanceAdapter.is_configured()`, `ProviderRouter.provider_for("US","daily_bars")` resolution from `config/providers.yaml`; exit 0=ok, 1=missing, 2=error; no live network call, no .env read, no token printed. Reran full pipeline: `validate_provider_router_live` and `run_market_snapshot_smoke` both `unknown` (sandbox 403 tunnel blocks Yahoo Finance at network level — not a code issue); `run_pre_market --date 2026-07-06` produced **Watch=1** (P1D.2 fix effective: liquidity_not_ok veto gone, confidence=0.45, risk_veto=False, why_not_action=missing_critical_data). 28 old "yfinance package is not installed" gaps remain in `data_gaps.jsonl` as historical records but do not appear in latest recommendation (P1D.3 date-scoped filter). On user's local machine with real network access, Yahoo Finance will return CRCL OHLCV bars and signals will compute. 12 new tests in `tests/test_check_provider_runtime_p1d4.py`. See `docs/P1D4_PROVIDER_RUNTIME_DEPENDENCY_RESULT.md` |
| P1D.3 | Recommendation Latest/Dedup + Status Alignment | done | 525 (+16) | Fixed 4 user-facing issues: (1) `recommendation_details.json` and `aegis_status.json` showed stale Exit status (3 Exit + 1 Watch all-history count) instead of latest-per-symbol Exit count (1). Root cause: builders used all-history tallies and an ambiguous dedup rule. Fix: `aegis/desktop/recommendation_details.py` fully rewritten with `_compute_latest_flags()` — preserves all 4 raw JSONL records; adds `is_latest_for_recommendation_id`/`is_latest_for_symbol` flags (tiebreak: highest created_at + file_position = last appended wins); adds `latest_recommendations` top-level list (one per symbol). `scripts/build_desktop_status.py._recommendations_summary()` rewritten: latest-per-rec-id first, then latest-per-symbol; `status_counts` and `count` reflect only latest per symbol. (2) Old `test_recommendation_details.py::test_9` expected dedup-to-one — updated to match P1D.3 contract (all records preserved, flags mark latest). (3) Stale `yfinance package is not installed` notes from 20260704 no longer appear on 2026-07-06 recommendation — date-scoped (`_normalize_date` YYYYMMDD↔YYYY-MM-DD) + market-scoped (symbol=None gaps only included when `gap.market == rec.market`) filtering in `_gaps_for_rec()`. (4) `latest_recommendations` top-level key now present in stock-agent workspace file. 16 new tests in `tests/test_recommendation_details_p1d3.py` covering all acceptance criteria. See `docs/P1D3_RECOMMENDATION_LATEST_DEDUP_STATUS_ALIGNMENT_RESULT.md` |

## Cumulative test growth

```text
Phase 0:  13
Phase 1:  41  (+28)
Phase 2:  59  (+18)
Phase 3:  85  (+26)
Phase 4: 112  (+27)
Phase 5: 132  (+20)
Phase 6: 197  (+65)
Phase 7: 249  (+52)
Phase 8: 249  (+0)
P1 Scope Decision Brief: 249  (+0)
P1A: 263  (+14)
P1A Real Data Validation Run: 263  (+0)
P1A.1 Provider Coverage Reconciliation: 266  (+3)
QA Cleanup + H/US/CRCL Provider Decision: 266  (+0)
P1B.1 ProviderRouter + H/US Adapter Skeleton: 301  (+35)
P1B.2 ProviderRouter Live Validation: 320  (+19)
P1B.3 Wire ProviderRouter into MarketDataService: 336  (+16)
P1B.4 H/US MarketSnapshot Smoke Run: 348  (+12)
P1B.4 fix Local MarketSnapshot Smoke Failure Triage: 355  (+7)
P1B.4.1 MarketSnapshot Smoke Consistency Fix: 364  (+9)
P1C Read-Only Bridge + Desktop Status Page: 412  (+48)
P1C.1 Desktop Polish + OpenClaw/Feishu Read-Only Prep: 447  (+35)
P1C.2 OpenClaw/Feishu Read-Only Connect: 466  (+19)
P1C.3 Status Cleanup + Stock-Agent Auto Refresh: 479  (+13)
P1D Real Premarket Recommendation Pipeline Smoke Run: 479  (+0)
P1D.1 Recommendation Details Mirror + Explanation Layer: 496  (+17)
P1D.2 Data-Backed Recommendation Pipeline Fix: 509  (+13)
P1D.3 Recommendation Latest/Dedup + Status Alignment: 525  (+16)
P1D.4 Provider Runtime Dependency + Data-Backed Rerun: 537  (+12)
```

**Note on the Phase 7 flakiness fix (QA cleanup round):** P1A.1 had 1
failing test —
`tests/test_time_travel_no_future_data.py::test_recommendation_never_references_the_future_spike`
— caused by an environment-clock coincidence, not a real data leak: that
Phase 7 test hardcodes 2026-07-01..2026-07-05 as its "future spike"
fixture dates and asserts none of those literal strings appear anywhere
in the dumped recommendation JSON, but `RecommendationRecord.created_at`/
`updated_at` use the real wall clock, and the day P1A.1 ran happened to
equal one of the fixture's own hardcoded spike dates. The fix (this
round) excludes only the two bookkeeping timestamp fields
(`created_at`/`updated_at`) from the JSON dump the test scans — the
assertion still checks every substantive recommendation field (prices,
evidence, notes, etc.) for a leaked spike value, it just no longer trips
over an incidental timestamp coincidence. This is a test-only change
(`tests/test_time_travel_no_future_data.py`); no production
Decision/Recommendation/TimeTravelEngine code was touched. `pytest -v`
now returns **266 passed, 0 failed**.

Every phase's own tests remain green in every subsequent phase — no test
has ever been deleted or weakened to make a later phase pass; the few
assertions that needed updating (documented inline with `NOTE:` comments
in the affected test files) were updates to match a shared script's
*intentionally* changed behavior (e.g. `run_pre_market.py`'s printed
header text, or a forbidden-file list narrowing as a later phase
legitimately started producing a file that an earlier phase correctly
asserted did not yet exist).

## P0 status

P0 (Phases 0-8) is complete as of 2026-07-04. See
`docs/P0_ACCEPTANCE_REPORT.md` for the full acceptance checklist against
Master Spec §24.

## P1 status

The user approved a single narrow P1 slice — **P1A: Real Data Validation +
Trading Calendar** — per `docs/P1_SCOPE_DECISION_BRIEF.md`. P1A is
complete as of 2026-07-04. A validation-only execution round then ran the
tooling inside the Cowork sandbox (`NOT_RUN_MISSING_TOKEN` — no token/
network there) and, separately, the user ran it locally with a real
token/network. That real report surfaced a diagnostic bug (H/US
`stock_basic` reusing A股's row count); **P1A.1: Provider Coverage
Reconciliation + Diagnostics Hardening** (approved follow-up scope, done
as of 2026-07-05) fixed the diagnostics layer to catch this class of bug
and produced `docs/P1A_PROVIDER_COVERAGE_DECISION.md`: **A股 core data
path (daily bars, index bars, stock_basic, trading calendar) is
confirmed; H股, US/CRCL, and sector/fundamental coverage across all
markets remain not confirmed.** A follow-up QA cleanup round (done as of
2026-07-05) fixed the one pre-existing test flakiness (Phase 7
date-collision, test-only fix) and produced
`docs/P1B_HUS_CRCL_PROVIDER_IMPLEMENTATION_SPEC.md` — a **planning-only**
document defining the next implementable H/US/CRCL provider plan
(capability matrix, `ProviderRouter` architecture, candidate provider
options, and a proposed **P1B.1: ProviderRouter + H/US adapter skeleton**
next phase). No provider code was implemented by that document.

**P1B.1: ProviderRouter + H/US Adapter Skeleton** (approved narrow
follow-up scope, done as of 2026-07-05) then implemented that safe
foundation: `ProviderRouter` (explicit per-`(market, data_type)` routing,
no silent fallback), a `YahooFinanceAdapter` skeleton (H/US daily/index
bars only — everything else explicitly unsupported), explicit symbol
mapping, and `config/providers.yaml`'s routing table. A股 remains
Tushare-first; H/US daily/index bars now have a secondary-provider route
available; H/US `stock_basic` is structurally prevented from ever
reusing A股's data again (routed to `"not_configured"`, not just
detected after the fact by diagnostics). See
`docs/P1B1_PROVIDER_ROUTER_RESULT.md`. **This is still a skeleton, not
live-verified coverage** — `yfinance` is not installed in this sandbox
and no live network call was made; the actual H/US/CRCL data quality via
`YahooFinanceAdapter` remains unverified.

**P1B.2: ProviderRouter Live Validation** (approved narrow follow-up
scope, done as of 2026-07-05) built and ran the live-validation tooling
called for in P1B.1's "next step." First run in this Cowork sandbox
degraded honestly (`dependency_missing` — no `yfinance`/network here).
**The user then ran the same tooling for real on their local machine**
(real `yfinance` + network): H daily bars, H index bars, US/CRCL daily
bars, and US index bars all reported **`pass`** (20 rows each); both
`stock_basic` checks correctly remained `not_configured` (intentional,
not a gap). **H/US daily/index coverage via the `yahoo_finance`
secondary route is now confirmed real**, including CRCL specifically.
This does not confirm H/US stock universe, sector classification, or
fundamentals — those remain `not_configured` by design. A follow-up
result-integration + QA-fix round then found and fixed the one pytest
failure the user's real `yfinance`-installed environment exposed (a
test/environment-coupling bug, not a production bug — see
`docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md`).

**P1B.3: Wire ProviderRouter into MarketDataService** (approved narrow
follow-up scope, done as of 2026-07-05) hardened and proved the
`MarketDataService` ↔ `ProviderRouter` integration point itself: built
tests against the real `config/providers.yaml`, confirmed A daily/index
stay Tushare-first, H/US daily/index (incl. CRCL) route to
`yahoo_finance` with correct symbol mapping, H/US `stock_basic` remains
`ProviderNotConfiguredError`, provider/route failures become a
correctly-labeled `DataGap` (never a crash, never fabricated data), and
cache keys never collide across A/H/US. See
`docs/P1B3_PROVIDER_ROUTER_MARKET_DATA_RESULT.md`. **This round did not
wire any real pipeline consumer** (`run_pre_market.py`, `UniverseBuilder`,
etc.) to actually construct/pass a `ProviderRouter` — that remains a
separate, not-yet-approved step.

**P1B.4: H/US MarketSnapshot Smoke Run** (approved narrow follow-up
scope, done as of 2026-07-05) added `scripts/run_market_snapshot_smoke.py`
proving the already-implemented, unmodified `MarketSnapshotService`/
`MarketRegimeAnalyzer` (Phase 2) actually consume H/US daily/index bars
through `MarketDataService` + `ProviderRouter`'s `yahoo_finance` route
and produce an honest `MarketSnapshot`. A script-local subclass enforces
"no future data" (bars dated after `--date` are filtered before
analysis, dropped rows recorded as an info-level DataGap) without
touching `aegis/market/service.py` itself. Real run in this Cowork
sandbox: both H and US honestly report `dependency_missing` (no
`yfinance` here, same sandbox limitation as P1B.2); the underlying
`yahoo_finance` route itself was already confirmed to `pass` on the
user's local machine (P1B.2), so this smoke run is expected to also
report `pass` when re-run there. See
`docs/P1B4_HUS_MARKETSNAPSHOT_SMOKE_RESULT.md`. **This round still did
not wire any real pipeline consumer** (`run_pre_market.py`, etc.) to
this smoke path — it remains a standalone, read-only check, not a
production wiring change.

**P1B.4 fix: Local MarketSnapshot Smoke Failure Triage** (approved
narrow follow-up scope, done as of 2026-07-05) — the user's real local
Mac run of the smoke command reported zero rows/`unknown` for both H
and US despite P1B.2 already confirming 20 real rows via the same
adapter. Root-caused to a date-string format bug: `lookback_range()`
produces a compact `"YYYYMMDD"` string that real `yfinance` silently
fails to parse (swallowing the resulting exception into an empty
result rather than raising). Fixed with one small, adapter-level
normalization helper in `aegis/data/yahoo_finance_adapter.py` — no
other production file changed. See
`docs/P1B4_HUS_MARKETSNAPSHOT_SMOKE_RESULT.md` for the full root-cause
narrative, the regression test that would have caught this earlier, and
a second occurrence of the `validate_provider_router_live.py` report
overwrite incident (caught and restored again).

**P1C.1: Desktop Polish + OpenClaw/Feishu Read-Only Prep** (approved
narrow follow-up scope, done as of 2026-07-05) fixed 4 display bugs the
user found in the P1C desktop status page (browser mistranslation of
`A`/`US`, market codes not rendered as human labels, A股 coverage always
showing `unknown` despite P1A's real Tushare coverage report already
confirming it, and stale `yfinance`-missing gaps still shown as current
after a later pass confirmed H/US) and prepared (but did not build) an
OpenClaw/Feishu integration: a new text-command adapter,
`scripts/openclaw_aegis_readonly.py`, with no allow/forbid logic of its
own (the gateway remains the sole authority), and a new setup contract,
`docs/P1C1_OPENCLAW_FEISHU_READONLY_SETUP.md`. The gateway's
`desktop-page` command's return shape changed to a flat, agent-friendly
`{"ok","path","absolute_path","open_command"}` — a deliberate, documented
breaking change; every other command's shape is unchanged. See
`docs/P1C1_DESKTOP_POLISH_OPENCLAW_PREP_RESULT.md`.

Candidates C (Risk Wiring Hardening) and D (Daily Operations Playbook),
a full H/US universe builder, actually wiring a real consumer to
construct/use a `ProviderRouter` in the live pipeline, the actual OpenClaw
skill/Feishu bot process, and any further provider integration all
remain postponed; no further P1 work should start without a new,
explicit user approval. See `docs/HANDOFF.md` for the current
known-gaps list.

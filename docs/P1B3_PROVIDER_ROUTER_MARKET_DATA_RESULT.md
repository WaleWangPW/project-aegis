# Project Aegis — P1B.3 Wire ProviderRouter into MarketDataService — Result

Produced per `Claude_Cowork_P1B3_WIRE_PROVIDER_ROUTER_MARKET_DATA.md`,
then confirmed/extended per `Claude_Cowork_P1B3_DATAGAP_PROVIDER_IMPACT_SCAN.md`
(read-only pre-change impact scan) and
`Claude_Cowork_P1B3_IMPLEMENT_AFTER_DATAGAP_SCAN.md` (implementation
round informed by that scan's findings). Narrow scope: let
`MarketDataService` actually consume `ProviderRouter`'s verified H/US
daily/index routes, without changing Decision/Expert/Dashboard behavior,
without implementing H/US universe, and without touching
UniverseBuilder/Signal Library/Expert Agents/Decision Engine.

## Summary

```text
A daily/index remains Tushare-first.
H daily/index can now be consumed by MarketDataService through ProviderRouter.
US/CRCL daily and US index can now be consumed by MarketDataService through ProviderRouter.
H/US stock_basic remains intentionally not_configured.
H/US universe is still not implemented.
Sector/fundamentals for H/US remain not confirmed.
DataGap provider labels are now route-specific where provider is known.
```

## DataGap provider impact scan (pre-change, read-only) and its outcome

Before this labeling change was made, a read-only scan confirmed:
`_record_gap` had 4 call sites in `aegis/market/service.py`; no
production code constructed a `DataGap` with a literal
`provider="market_data_service"` string (the value already lived in one
centralized fallback constant); and no test anywhere asserted on
`gap["provider"]` at the time, so changing the field's value from a
hardcoded generic label to a route-specific one could not break any
existing assertion. The implementation below is exactly what that scan
cleared the way for — the labeling now distinguishes `"yahoo_finance"`/
`"tushare"`/the generic fallback, and 4 tests were added specifically to
pin those three cases down going forward (see "Tests" below).

## What "wiring" actually meant here

`MarketDataService` already accepted a `provider_router` argument since
P1B.1, and — because `ProviderRouter` duck-types identically to a plain
provider — a caller who passes `provider_router=` was already
mechanically routed per `config/providers.yaml`'s table (A → Tushare,
H/US daily/index → `yahoo_finance`). P1B.3's job was to prove that
integration point is actually correct and safe to rely on, and to
harden its diagnostics:

- **`aegis/data/provider_router.py`**: added `ProviderRouter.route_name_for(market, data_type)`
  — a small, non-raising diagnostic lookup of the configured route name
  (or `None` if nothing is configured at all). Used only to label
  `DataGap`s; never used for control flow (routing decisions still go
  entirely through `_route_name`/`provider_for`'s raising behavior).
- **`aegis/market/service.py`**: `get_daily_bars_cached`/
  `get_index_bars_cached` now label every recorded `DataGap` with the
  actual failing provider/route (via `route_name_for`, falling back to
  a generic label for a plain non-router provider) instead of a
  hardcoded `"market_data_service"` string, include the failing
  exception's type in the message, and always populate
  `consumer_impact`. `get_latest_close()` needed no changes — it already
  delegates to `get_daily_bars_cached()`, so H/US routing flows through
  it automatically once bars are wired.
- No changes to `DataCache` — its cache path (`root_dir/market/data_type/key`)
  already separates every market and data type; P1B.3 only added tests
  proving H/US Yahoo results and A股 Tushare results never collide,
  even when the same literal symbol string is requested across markets.
- `config/providers.yaml`, `scripts/check_provider_router.py`: unchanged
  — the routing table and the config-only diagnostic CLI already
  correctly describe this integration; no refinement was needed.

## Route table (unchanged from P1B.1, now actually exercised through MarketDataService)

| Market | Data type | Route |
|---|---|---|
| A | daily_bars | Tushare-first (existing behavior, unchanged) |
| A | index_bars | Tushare-first (existing behavior, unchanged) |
| H | daily_bars | `ProviderRouter` → `yahoo_finance` (confirmed real, P1B.2) |
| H | index_bars | `ProviderRouter` → `yahoo_finance` (confirmed real, P1B.2) |
| US | daily_bars | `ProviderRouter` → `yahoo_finance` (confirmed real, P1B.2, incl. CRCL) |
| US | index_bars | `ProviderRouter` → `yahoo_finance` (confirmed real, P1B.2) |
| H | stock_basic | `not_configured` (intentional, unchanged) |
| US | stock_basic | `not_configured` (intentional, unchanged) |

## No silent fallback (verified)

For every one of `not_configured`, `unsupported`, and a simulated
`dependency_missing`/network-flavored `ProviderError`:

- `MarketDataService` returns an empty `DataFrame` (or `None` from
  `get_latest_close`), exactly as it already did for a plain provider
  failure — no new return-shape branch was introduced.
- A `DataGap` is recorded, labeled with the actual failing route
  (`"tushare"`, `"yahoo_finance"`, or the generic fallback label when no
  route is configured at all) and the failing exception's type.
- H/US `stock_basic` is never satisfied by A股's data — confirmed again
  this round directly against the **real** `config/providers.yaml` (not
  just a hand-written test fixture), with an assertion that the fake
  Tushare provider was never called for it.
- No route is ever silently retried through an unapproved provider.

## Cache behavior (verified, unchanged)

`DataCache.get_path(market, data_type, key)` was already
market/data_type-scoped since Phase 1. P1B.3 added a test that requests
the same symbol string across A/H/US and confirms: three distinct cache
files are written, each market's cached result carries its own route's
data (never another market's), and swapping the `yahoo_finance` provider
for a failing one afterward does not disturb the already-cached A股
Tushare result — proving no cross-market cache collision is possible.

## Tests

16 new tests total across both implementation rounds:

- `tests/test_provider_router_market_data_integration.py` (14) — built
  against a `ProviderRouter` constructed from the **real**
  `config/providers.yaml` (loaded from disk, not retyped), with fake
  `tushare`/`yahoo_finance` instances substituted in: A daily/index stay
  on Tushare; H daily/index and US daily/index (including CRCL, treated
  as an ordinary sample symbol) route to `yahoo_finance` with correct
  symbol/index mapping applied; H/US `stock_basic` remains
  `ProviderNotConfiguredError`; a `yahoo_finance`-side `ProviderError`
  becomes a `DataGap` labeled `provider == "yahoo_finance"`; a
  Tushare-side `ProviderError` becomes a `DataGap` labeled
  `provider == "tushare"` — both never a crash; a route missing entirely
  from the config (distinct from the `"not_configured"` sentinel) also
  degrades honestly, falling back to the generic
  `provider == "market_data_service"` label since no specific route is
  known; cache-key separation across A/H/US; `get_latest_close()`
  returns the correct price for H/US when the route succeeds, and
  returns `None` while recording a correctly-labeled (`"yahoo_finance"`)
  `DataGap` when the route fails; and a source-inspection test
  confirming `aegis/market/service.py`/`aegis/data/provider_router.py`
  never import `dotenv`, touch `os.environ`, reference `TUSHARE_TOKEN`,
  or construct a `TushareAdapter` directly.
- `tests/test_market_data_service.py` (2) — `consumer_impact` and a
  descriptive error-type message are present on every recorded gap, for
  both the "provider raised" and "empty result" paths, using a plain
  (non-router) provider; one of these pins the generic fallback label
  (`provider == "market_data_service"`) for a service-level failure with
  no identifiable route, per the DataGap impact scan's finding that this
  case must remain distinguishable from a real Yahoo/Tushare failure.

Together these 3 tests (one per source: `tests/test_provider_router_market_data_integration.py:196`
Yahoo-route case, `:213` Tushare-route case, and
`tests/test_market_data_service.py:110` / `tests/test_provider_router_market_data_integration.py:247`
generic-fallback case) are exactly the 4 assertions the pre-change scan
identified and confirms none were weakened — the labeling logic changes
their expected values, not whether they check a specific value at all.

`pytest -v`: **336 passed, 0 failed** (320 before P1B.3 + 15 from the
first implementation pass + 1 added this round to close the
"`get_latest_close()` records a gap on route failure" case explicitly).
Verified both with `yfinance` installed and without it in this Cowork
sandbox (same environment-independence discipline established in the
P1B.2 QA-fix round).

## Commands run

```bash
pytest -v
python scripts/check_provider_router.py
```

`check_provider_router.py` output is unchanged from P1B.1/P1B.2 — still
a config/wiring-only report, no live call, confirms the route table and
symbol mappings above.

**`scripts/validate_provider_router_live.py` was deliberately not
re-run this round.** The first P1B.3 implementation pass ran it as a
smoke check and it correctly degraded to `dependency_missing` (no
`yfinance` in this sandbox) — but doing so **overwrote
`data/processed/provider_router/provider_router_live_report.json`**,
replacing the user's real local P1B.2 pass results (4 `pass`, 2
`not_configured`). That was caught and the file was restored immediately
after (see `docs/HANDOFF.md`'s archived P1B.3 section for that
incident). To avoid repeating it, this round's changes were validated
entirely through `pytest -v` and `check_provider_router.py`, both of
which never touch that report file. No live Yahoo Finance network was
required by, or exercised in, any unit test.

## Explicit non-goals confirmed untouched

- No H/US stock universe, `stock_basic`, sector classification, or
  fundamentals implementation.
- `aegis/universe/builder.py` (UniverseBuilder), `aegis/signals/`,
  `aegis/experts/`, `aegis/decision/`, `aegis/recommendation/` — all
  untouched (confirmed by file timestamp).
- `dashboard/index.html` — byte-identical (confirmed by diff; also
  covered by the existing `test_dashboard_index_html_unchanged` test).
- No OpenClaw/Feishu bridge work.
- No broker integration, real trading, or PaperTrade creation from
  chat/bridge/command.
- No composite/weighted scoring.
- CRCL is not special-cased — it appears only as an ordinary US sample
  symbol in tests, exactly like `00700.HK`/`SPX`.
- No token value read, printed, or logged — confirmed by grep and by a
  dedicated test inspecting the actual module source of both changed
  production files.

## Known gaps (carried forward, not addressed this round)

- H/US stock universe, `stock_basic`, sector classification, and
  fundamentals remain unimplemented — H/US candidates still must come
  from `config/holdings.yaml`/a manual watchlist only.
- No real application entry point (`scripts/run_pre_market.py`,
  `UniverseBuilder`, `MarketSnapshotService`, etc.) has been changed to
  actually construct a `ProviderRouter` and pass it to
  `MarketDataService` in the live pipeline — this round only proves the
  integration point itself is correct; wiring an actual consumer is a
  separate, not-yet-approved step.
- P1B.2's real validation was a single ~20-row window on one occasion —
  it still does not establish long-term reliability, rate-limit
  behavior, or historical-depth availability of the `yahoo_finance`
  route.

## Next recommendation

Only after user approval, one of:

A. A narrow follow-up that actually constructs a real `ProviderRouter`
   (Tushare + `YahooFinanceAdapter`) inside one real consumer (e.g.
   `scripts/run_pre_market.py` or `MarketSnapshotService`) and runs an
   H/US smoke pass, with an explicit before/after diff proving no
   existing fixture test's decision/return result silently changed.
B. P1C — an OpenClaw/Feishu read-only bridge (unrelated to provider
   work).

Do not start either without explicit user approval.

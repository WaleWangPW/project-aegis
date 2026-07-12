# Project Aegis — P1B.1 ProviderRouter + H/US Adapter Skeleton — Result

Produced per `Claude_Cowork_P1B1_PROVIDER_ROUTER_HUS_ADAPTERS.md`. This
round implements the **safe foundation** the product decision called
for — a router + secondary-provider skeleton — not a full H/US universe
or live-verified coverage.

## What was implemented

- **`aegis/data/provider_router.py` — `ProviderRouter`**: routes every
  `(market, data_type)` request to a named provider instance per
  `config/providers.yaml`'s explicit routing table. No silent fallback:
  a pair with no route raises `ProviderNotConfiguredError`; a pair
  explicitly marked `"unsupported"` raises `ProviderUnsupportedError`.
  Implements the same duck-typed method shape as `TushareAdapter`
  (`get_daily_bars`/`get_index_bars`/`get_stock_basic`/`get_fundamentals`/
  `get_sector_classification`/`get_trading_calendar`), so it is a drop-in
  replacement anywhere a single provider was previously used.
- **`aegis/data/yahoo_finance_adapter.py` — `YahooFinanceAdapter`**: a
  thin secondary adapter for H/US daily bars and index bars. Labels every
  result `source="yahoo_finance"`; normalizes to Aegis's own
  `trade_date`/`open`/`high`/`low`/`close`/`vol` convention with
  deterministic `YYYYMMDD` date formatting. `get_stock_basic`,
  `get_fundamentals`, `get_sector_classification`, and
  `get_trading_calendar` all explicitly raise `ProviderUnsupportedError`
  — this skeleton adapter does not claim to provide a full universe,
  fundamentals, sector data, or a real trading calendar. The `yfinance`
  package is imported lazily/defensively (same convention as
  `TushareAdapter`'s lazy `tushare` import) — not installed in this
  Cowork sandbox, and never required for tests (every test injects a
  fake client).
- **`aegis/data/symbol_mapping.py` — `SymbolMapper`**: explicit,
  provider-specific symbol/index-code translation, sourced from
  `config/providers.yaml`'s `symbol_mapping` section. A provider with no
  mapping table at all (e.g. Tushare) passes symbols through unchanged.
  US may fall back to identity when unconfigured (many US tickers are
  already Yahoo-compatible); H must not — an unmapped H symbol raises
  `SymbolMappingError` rather than guessing.
- **`config/providers.yaml`** (new): the routing table. A股 stays
  Tushare-first for every capability. H/US `daily_bars`/`index_bars`
  route to `yahoo_finance`. H/US `stock_basic`, `sector_classification`,
  and `fundamentals` are explicitly `"not_configured"` — never satisfied
  by reusing A股's data (the exact P1A.1 bug, now prevented structurally
  at the routing layer, not just detected after the fact).
- **`aegis/data/providers.py`**: added `ProviderNotConfiguredError` and
  `ProviderUnsupportedError` (both `ProviderError` subclasses) — the
  shared vocabulary `ProviderRouter`, `YahooFinanceAdapter`, and
  diagnostics all use to distinguish "no route decided yet" / "known
  capability gap" from a plain unexpected provider failure.
- **`aegis/data/provider_diagnostics.py`**: `_run_call`/`_check` now
  catch `ProviderNotConfiguredError`/`ProviderUnsupportedError` *before*
  the generic `ProviderError` branch, mapping them to
  `ProviderCheck.status` values `"not_configured"`/`"unsupported"` (both
  already part of P1A.1's hardened `CheckStatus` vocabulary — no new
  status values were needed). This means `run_checks_for_market` and
  `validate_real_data()` already understand a `ProviderRouter` passed in
  as their `provider` argument, with no further changes required there.
- **`aegis/market/service.py` — `MarketDataService`**: now accepts either
  `provider` (unchanged, existing behavior) or `provider_router`
  (`ProviderRouter`) — both are duck-typed identically, so the service's
  caching/`DataGap`-recording logic needed zero branching to support
  this. Every existing call site (`scripts/run_pre_market.py`,
  `scripts/run_close.py`, `aegis/backtest/time_travel.py`, every existing
  test) is unaffected — they all already pass `provider=` by keyword.
- **`scripts/check_provider_router.py`** (new CLI): prints the route
  table, validates every configured symbol/index mapping, and reports
  `tushare`/`yfinance` package availability — writes
  `data/processed/provider_diagnostics/provider_router_report.json`.
  Deliberately does **not** attempt any live provider call this round
  (see "Known gaps" below) — every route is reported `"skipped"` with an
  explicit reason, never a crash, and never reads or prints a token
  value (it only ever touches `config/providers.yaml` and package import
  checks).
- **35 new tests** across `tests/test_provider_router.py`,
  `tests/test_yahoo_finance_adapter.py`, `tests/test_symbol_mapping.py`,
  `tests/test_check_provider_router.py` — all fixture/fake-provider data,
  no real network. Covers: A股 routes to Tushare; H/US daily/index bars
  route to the secondary adapter with correct symbol/index mapping
  applied; H/US `stock_basic` raises `ProviderNotConfiguredError` and
  never falls back to A股's data; a route marked `"unsupported"` raises
  `ProviderUnsupportedError`; `YahooFinanceAdapter` normalizes fake OHLCV
  data and returns an empty DataFrame (never fake bars) on an empty
  result; `MarketDataService` accepts a `provider_router` and still
  records a `DataGap` on a routed provider failure; `scripts/check_provider_router.py`
  writes a valid report with zero live network.

`pytest -v`: **301 passed, 0 failed** (266 before this round + 35 new).

## What was NOT implemented (explicitly out of scope this round)

- No full H/US stock universe builder — H/US candidates continue to come
  from `config/holdings.yaml`/a manual watchlist only, per the task's own
  §4.3.
- No live verification that `YahooFinanceAdapter` actually works against
  the real `yfinance` package or real Yahoo Finance data — `yfinance` is
  not installed in this Cowork sandbox and no live network call was made
  anywhere in this round (every test uses a fake/injected client).
- No fundamentals, sector classification, or trading calendar via the
  secondary provider — all explicitly `ProviderUnsupportedError` in
  `YahooFinanceAdapter`, and `"not_configured"`/`"unsupported"` in
  `config/providers.yaml`'s routing table.
- No OpenClaw/Feishu bridge work.
- No Decision Engine, Recommendation status rule, or Expert Agent
  changes.
- No Dashboard UI changes (`dashboard/index.html` confirmed byte-identical).
- No broker integration, real trading, or manual PaperTrade creation.
- No composite/weighted scoring.
- CRCL is not special-cased anywhere in this round's code — it appears
  only as a config sample value (`config/providers.yaml`'s
  `symbol_mapping.yahoo_finance.US.symbols.CRCL`) and in test fixtures,
  exactly like any other symbol. `aegis/portfolio/holdings_loader.py` is
  unchanged.
- No token value was read, printed, or logged anywhere this round —
  `.env` was never opened; `scripts/check_provider_router.py` never
  touches `os.environ` at all.

## How to run router diagnostics

```bash
python scripts/check_provider_router.py
python scripts/check_provider_router.py --config config/providers.yaml --output data/processed/provider_diagnostics/provider_router_report.json
```

Prints the route table and symbol-mapping validation results, reports
whether `tushare`/`yfinance` are installed, and writes the JSON report.
Every route is reported `"skipped"` this round (see "Known gaps" below)
— this is a config/wiring sanity check, not a live coverage validator.

To exercise the router against real data, a caller constructs it directly:

```python
from aegis.data.provider_router import ProviderRouter
from aegis.data.tushare_adapter import TushareAdapter
from aegis.data.yahoo_finance_adapter import YahooFinanceAdapter
import yaml

config = yaml.safe_load(open("config/providers.yaml"))
router = ProviderRouter(
    providers={"tushare": TushareAdapter.from_env(), "yahoo_finance": YahooFinanceAdapter()},
    routing_config=config,
)
```

This has not been run against real data from this Cowork sandbox (no
`yfinance` installed, no outbound network, and per this task's explicit
instruction, no token was read or touched).

## H/US coverage still requiring live local validation

- Whether `YahooFinanceAdapter` actually returns usable H/US daily/index
  bars once `yfinance` is installed and network is available — this
  round only proves the adapter *shape* is correct against fake data.
- Whether the configured symbol mappings (`"00700.HK"` → `"0700.HK"`,
  `"HSI.HI"` → `"^HSI"`, `"SPX"` → `"^GSPC"`) are actually the correct
  Yahoo Finance tickers — these were written from general knowledge of
  Yahoo's naming convention, not verified against a live response from
  this sandbox.
- A股 core data path remains the only **live-confirmed** coverage (per
  `docs/P1A_PROVIDER_COVERAGE_DECISION.md`); this round changes nothing
  about that.

## Explicit statements (per task §9/§10)

- **CRCL is not special-cased.** It is only a holding record
  (`config/holdings.yaml`) and a config/test sample symbol
  (`config/providers.yaml`, test fixtures) — no business logic anywhere
  branches on `symbol == "CRCL"`.
- **OpenClaw/Feishu bridge work is still postponed.** None was done this
  round, none is implied by anything implemented here.

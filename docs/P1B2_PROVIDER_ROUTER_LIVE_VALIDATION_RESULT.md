# Project Aegis — P1B.2 ProviderRouter Live Validation — Result

Produced per `Claude_Cowork_P1B2_PROVIDER_ROUTER_LIVE_VALIDATION.md`, then
updated per `Claude_Cowork_P1B2_RESULT_INTEGRATION_QA_FIX.md` with the
user's real local validation result. Narrow scope: build and run an
honest live-validation path for `ProviderRouter`'s H/US **secondary**
(`yahoo_finance`) route only. Never touches Tushare, `.env`,
`os.environ`, or `TUSHARE_TOKEN`.

## Result (local machine, real network — not Cowork sandbox)

```text
H daily route: PASS
H index route: PASS
US/CRCL daily route: PASS
US index route: PASS
H stock_basic: NOT_CONFIGURED intentionally
US stock_basic: NOT_CONFIGURED intentionally
```

This validates daily/index bar routes only. It does not validate H/US
stock universe, sector classification, fundamentals, or provider-level
reliability over longer date ranges.

The user ran `python scripts/validate_provider_router_live.py` locally
with `yfinance` installed and real outbound network — the first real,
non-degraded run of this tooling. The report file
(`data/processed/provider_router/provider_router_live_report.json`,
synced back into this repo via the Vault) is reproduced below.

## Command run (local)

```bash
python scripts/validate_provider_router_live.py
```

Local result summary:

```text
CHECK_EXIT_CODE=0
LIVE_EXIT_CODE=0
```

Exit code 0 — correct, since at least one H/US daily/index route
reported `pass` (all four did).

## Generated report (real, local)

```text
data/processed/provider_router/provider_router_live_report.json
```

```json
{
  "run_id": "provider_router_live_20260704_173128",
  "created_at": "2026-07-05T01:31:35.612444+08:00",
  "network_attempted": true,
  "checks": [
    {"check_name": "h_daily_bars", "market": "H", "data_type": "daily_bars", "provider": "yahoo_finance", "sample_symbol": "00700.HK", "mapped_symbol": "0700.HK", "status": "pass", "rows_returned": 20, "warning": null, "error_type": null},
    {"check_name": "h_index_bars", "market": "H", "data_type": "index_bars", "provider": "yahoo_finance", "sample_symbol": "HSI.HI", "mapped_symbol": "^HSI", "status": "pass", "rows_returned": 20, "warning": null, "error_type": null},
    {"check_name": "h_stock_basic", "market": "H", "data_type": "stock_basic", "provider": "not_configured", "sample_symbol": null, "mapped_symbol": null, "status": "not_configured", "rows_returned": null, "warning": "stock_basic for market='H' is explicitly routed to \"not_configured\" — no real provider has been approved for this capability yet.", "error_type": "ProviderNotConfiguredError"},
    {"check_name": "us_daily_bars", "market": "US", "data_type": "daily_bars", "provider": "yahoo_finance", "sample_symbol": "CRCL", "mapped_symbol": "CRCL", "status": "pass", "rows_returned": 20, "warning": null, "error_type": null},
    {"check_name": "us_index_bars", "market": "US", "data_type": "index_bars", "provider": "yahoo_finance", "sample_symbol": "SPX", "mapped_symbol": "^GSPC", "status": "pass", "rows_returned": 20, "warning": null, "error_type": null},
    {"check_name": "us_stock_basic", "market": "US", "data_type": "stock_basic", "provider": "not_configured", "sample_symbol": null, "mapped_symbol": null, "status": "not_configured", "rows_returned": null, "warning": "stock_basic for market='US' is explicitly routed to \"not_configured\" — no real provider has been approved for this capability yet.", "error_type": "ProviderNotConfiguredError"}
  ],
  "summary": {
    "pass_count": 4, "fail_count": 0, "unknown_count": 0, "skipped_count": 0,
    "not_configured_count": 2, "dependency_missing_count": 0,
    "network_unavailable_count": 0, "unsupported_count": 0
  }
}
```

`network_attempted: true` — unlike the earlier Cowork-sandbox run, every
bars check actually reached a real Yahoo Finance call this time (not
just a dependency check).

## Status table

| Check | Market | Data type | Route | Sample | Mapped | Status | Rows |
|---|---|---|---|---|---|---|---|
| h_daily_bars | H | daily_bars | yahoo_finance | `00700.HK` | `0700.HK` | **pass** | 20 |
| h_index_bars | H | index_bars | yahoo_finance | `HSI.HI` | `^HSI` | **pass** | 20 |
| h_stock_basic | H | stock_basic | not_configured | — | — | not_configured (intentional) | — |
| us_daily_bars (CRCL) | US | daily_bars | yahoo_finance | `CRCL` | `CRCL` | **pass** | 20 |
| us_index_bars | US | index_bars | yahoo_finance | `SPX` | `^GSPC` | **pass** | 20 |
| us_stock_basic | US | stock_basic | not_configured | — | — | not_configured (intentional) | — |

- **Was CRCL available via the secondary provider?** Yes — confirmed
  real: `us_daily_bars` (sample `CRCL`) returned 20 real rows from
  `yahoo_finance` on the user's local machine. CRCL was never
  special-cased in code — it is treated exactly like `00700.HK`/`SPX` (a
  config/test sample symbol only), and this result confirms the generic
  route works for it the same as any other US symbol.
- **Does H/US `stock_basic` remain blocked?** Yes — both still report
  `not_configured`, raised structurally by `ProviderRouter` before any
  provider is touched (unchanged from P1B.1's `config/providers.yaml`).
  This is intentional, not a gap this round needed to close.
- **Were the P1B.1 symbol mappings correct?** Yes, confirmed for real
  this time: `00700.HK`→`0700.HK`, `HSI.HI`→`^HSI`, `SPX`→`^GSPC` all
  resolved to tickers that Yahoo Finance actually returned real bars for.

## Scope of what this confirms

This validates **daily/index bar routes only**. It does **not** validate:

- H/US stock universe (`stock_basic` remains `not_configured` by
  design — no universe builder exists yet).
- Sector classification or fundamentals (still `not_configured` for
  H/US in `config/providers.yaml`).
- Provider-level reliability over longer date ranges, rate limits, or
  repeated-call behavior — this was a single small-window (~20 row)
  check, not a stress test.

## Test result

```bash
pytest -v
```

**320 passed, 0 failed.**

A pytest failure surfaced when the user ran the suite locally
(`PYTEST_EXIT_CODE=1`) after having installed real `yfinance` to run the
live validation above. Root cause (confirmed by reproducing it in this
Cowork sandbox with `yfinance` installed): `tests/test_yahoo_finance_adapter.py::test_no_client_configured_raises_provider_error`
passed `client=None` expecting `YahooFinanceAdapter` to have no
client/package available at all, but `YahooFinanceAdapter.__init__`
falls back to the module-level `yf` symbol when `client=None` (the same
lazy-import convention `TushareAdapter` uses for `tushare`) — so once
`yfinance` is genuinely installed in the environment (exactly what a
real local live-validation run requires), that fallback resolves to the
real package, the test's `get_daily_bars` call reaches real (blocked or
real) network instead of raising `ProviderError`, and the test fails
with `DID NOT RAISE ProviderError`.

This was a test/environment-coupling bug, not a production code bug —
the adapter's fallback-to-real-`yf` behavior is correct and intentional.
Fix: the test now uses `monkeypatch.setattr(yahoo_finance_adapter_module, "yf", None)`
to force the "no package available" condition deterministically,
regardless of whether the real `yfinance` package happens to be
installed in whatever environment `pytest` runs in. Verified
`pytest -v` returns 320 passed, 0 failed both with `yfinance` installed
and without it.

## Known gaps

- H/US `stock_basic`/`sector_classification`/`fundamentals` remain
  `not_configured` — no full H/US universe builder exists yet; H/US
  candidates must continue to come from `config/holdings.yaml`/a manual
  watchlist only.
- This round validated a single ~20-row window on one occasion — it does
  not establish long-term reliability, rate-limit behavior, or
  historical-depth availability of the `yahoo_finance` secondary route.
- `--start`/`--end` CLI arguments remain informational only; the
  underlying adapter/router call uses a fixed recent window internally.

## Next recommendation

Only after user approval: decide whether to wire the now-verified H/US
daily/index `ProviderRouter` routes into `MarketDataService` for real
consumers (P1B.3), or continue other provider work (full H/US universe,
sector/fundamentals). Do not start P1B.3 without that explicit approval.

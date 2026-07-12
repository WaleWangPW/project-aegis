# Project Aegis — P1A Real Data Validation Result

> **Update history:** the original version of this document (2026-07-04)
> recorded a Cowork-sandbox-only run with status `NOT_RUN_MISSING_TOKEN`
> (no `TUSHARE_TOKEN`, no outbound network in that sandbox). The user has
> since run `scripts/validate_real_data.py` **locally**, with a real
> `TUSHARE_TOKEN` and network access. This document is fully rewritten to
> reflect that real report, per
> `Claude_Cowork_P1A1_PROVIDER_COVERAGE_RECONCILIATION.md`. The prior
> sandbox `NOT_RUN_MISSING_TOKEN` finding is preserved in `docs/HANDOFF.md`'s
> archive section for history, not repeated here.

## Status

**PARTIAL**

Real token + real network were available for this run. Some P0 data
categories are confirmed working (A股 daily bars, index bars,
`stock_basic`, trading calendar); most others returned empty results or —
in two cases — results now identified as a diagnostic artifact rather
than real coverage. See `docs/P1A_PROVIDER_COVERAGE_DECISION.md` for the
authoritative confirmed/not-confirmed breakdown and next-step decision.

## Commands Run

By the user, locally (not in this Cowork sandbox):

```bash
python scripts/validate_real_data.py --output data/processed/provider_diagnostics/provider_coverage_report.json
```

In this Cowork sandbox, as part of P1A.1 (Provider Coverage
Reconciliation + Diagnostics Hardening):

```bash
pytest -v
```

## Test Result

- `pytest -v`: **265 passed, 1 failed** (266 collected). The 1 failure is
  a pre-existing, unrelated, environment-clock issue in a Phase 7 test
  (`tests/test_time_travel_no_future_data.py::test_recommendation_never_references_the_future_spike`)
  — see `docs/DEVELOPMENT_STATUS.md`'s "Note on P1A.1's 266 figure" for
  the full explanation. It is out of P1A.1's approved scope (no
  TimeTravelEngine changes) and unrelated to provider coverage.

## Provider Coverage Report

Path:

- `data/processed/provider_diagnostics/provider_coverage_report.json`
  (the real report, generated locally by the user with a live
  `TUSHARE_TOKEN`; `token_present: true`, `network_available: true`).

Raw per-check results as generated (before P1A.1's diagnostics hardening
existed — see "Real report vs. hardened diagnostics" below):

| Check | Market | Status (raw) | Rows | Note |
|---|---|---|---:|---|
| daily_bars | A | pass | 21 | `000001.SZ` |
| index_bars | A | pass | 21 | `000300.SH` |
| stock_basic | A | pass | 5534 | |
| sector_classification | A | unknown | 0 | empty result |
| fundamentals | A | unknown | 0 | empty result |
| trading_calendar | A | pass | 31 | |
| daily_bars | H | unknown | 0 | `00700.HK` |
| index_bars | H | unknown | 0 | `HSI.HI` |
| stock_basic | H | pass | 5534 | **same row count as A股 — see below** |
| sector_classification | H | unknown | 0 | empty result |
| fundamentals | H | unknown | 0 | empty result |
| trading_calendar | H | pass | 31 | |
| daily_bars | US | unknown | 0 | `CRCL` |
| index_bars | US | unknown | 0 | `SPX` |
| stock_basic | US | pass | 5534 | **same row count as A股 — see below** |
| sector_classification | US | unknown | 0 | empty result |
| fundamentals | US | unknown | 0 | `CRCL`, empty result |
| trading_calendar | US | pass | 31 | |

Summary as generated: `pass_count: 8, fail_count: 0, skipped_count: 0,
unknown_count: 10, critical_gaps: []`.

**Category summary:**

- **A 股 coverage**: confirmed for daily bars, index bars, stock_basic,
  trading calendar. Sector classification and fundamentals returned
  empty results — not confirmed either way.
- **H 股 coverage**: not confirmed. Daily bars, index bars, sector
  classification, and fundamentals all returned 0 rows. `h_stock_basic`
  reported `pass` with 5534 rows — but that is the exact same row count
  as A股's `stock_basic`, which is not a coincidence (see below) — **not
  confirmed real H股 stock universe coverage.**
- **US coverage**: not confirmed. Same pattern as H — daily bars, index
  bars, sector classification, and fundamentals returned 0 rows;
  `us_stock_basic`'s 5534-row "pass" has the same false-positive
  explanation as H's.
- **Index data coverage**: not confirmed for H/US (`HSI.HI`/`SPX` both 0
  rows); confirmed for A (`000300.SH`, 21 rows).
- **Daily bars coverage**: confirmed for A (`000001.SZ`); not confirmed
  for H (`00700.HK`) or US (`CRCL`) — both 0 rows.
- **Fundamentals coverage**: not confirmed for any market (all three
  returned empty results).
- **Trading calendar coverage**: reported `pass` with 31 rows for all
  three markets. Per the task's own required interpretation
  (`Claude_Cowork_P1A1_PROVIDER_COVERAGE_RECONCILIATION.md` §3.1), A股's
  trading calendar is treated as confirmed. **Residual caveat, not acted
  on this round:** `TushareAdapter.get_trading_calendar(market, ...)` has
  the same structural pattern as `get_stock_basic` — it ignores its
  `market` argument and always calls `pro.trade_cal(exchange="", ...)`.
  P1A.1's cross-market reconciliation was scoped narrowly to
  `stock_basic` only (the one case the task doc explicitly flagged as
  suspicious), so H/US trading_calendar's "pass" is left as reported.
  Flagged here as a known, not-yet-acted-on residual limitation for
  future review — not silently accepted as proof of real H/US calendar
  coverage.
- **CRCL coverage**: **not confirmed.** `us_daily_bars` (sample symbol
  `CRCL`) and `us_fundamentals` (also keyed on `CRCL`) both returned 0
  rows. CRCL is a real holding, but this report gives no evidence Tushare
  actually serves its price/fundamental data. See
  `docs/P1A_PROVIDER_COVERAGE_DECISION.md`'s CRCL impact section.

## Real report vs. hardened diagnostics (P1A.1)

This exact JSON file was generated *before* P1A.1's diagnostics hardening
existed. P1A.1 (this round) changed `aegis/data/provider_diagnostics.py`
and `aegis/data/live_validation.py` so that **the next time**
`scripts/validate_real_data.py` is run against the real provider:

- `h_stock_basic`/`us_stock_basic` would no longer report a bare `pass` —
  `reconcile_cross_market_checks()` detects that a non-A股 market's
  `stock_basic` check returned the exact same `rows_returned` as A股's,
  and downgrades it to `unsupported` (with an explanatory `DataGap`),
  reproducing and catching the pattern seen in this real report. This is
  exercised by
  `tests/test_provider_diagnostics.py::test_provider_diagnostics_flags_stock_basic_reusing_a_share_data`
  using a fake provider that reproduces the bug.
- The ten `unknown` (empty-result) checks above would now be labeled
  `unknown_empty` — same meaning, clearer name.
- Any future permission/entitlement-flavored Tushare error would be
  labeled `permission_denied` instead of a generic `fail`.

This document's conclusions (above, and in
`docs/P1A_PROVIDER_COVERAGE_DECISION.md`) already treat the H/US
`stock_basic` "pass" as **not confirmed**, applying the same judgment the
hardened diagnostics would now apply automatically. The raw JSON file on
disk has not been regenerated this round (no real token/network in this
Cowork sandbox) — only its *interpretation* has been corrected.

## Data Gaps

- `a_sector_classification`, `a_fundamentals`: empty result, coverage not
  confirmed.
- `h_share_daily_bars`, `h_index_bars`, `h_sector_classification`,
  `h_fundamentals`: empty result, coverage not confirmed.
- `us_daily_bars`, `us_index_bars`, `us_sector_classification`,
  `us_fundamentals`: empty result, coverage not confirmed. `us_daily_bars`
  is the CRCL holding specifically.
- `h_stock_basic`, `us_stock_basic`: reported `pass` in the raw file, but
  reclassified here (and by P1A.1's hardened diagnostics on the next run)
  as **not confirmed** — suspected reuse of A股 universe data due to
  `TushareAdapter.get_stock_basic` ignoring its `market` argument.
- Residual, not-yet-reclassified: H/US `trading_calendar` "pass" shares
  the same underlying adapter limitation (ignores `market`) but was left
  as-is per the task's explicit required interpretation — see the
  Trading calendar coverage bullet above.

## Safe Conclusion

**Verified this round (P1A.1):**

- A股's core live data path — daily bars, index bars, `stock_basic`,
  trading calendar — is confirmed working against a real Tushare
  account.
- The `h_stock_basic`/`us_stock_basic` "pass" in the raw report is a
  diagnostic artifact, not real H/US universe coverage — root-caused to
  `TushareAdapter.get_stock_basic(market)` ignoring its `market`
  parameter (verified by reading `aegis/data/tushare_adapter.py`, not
  guessed).
- The diagnostics layer (`aegis/data/provider_diagnostics.py`,
  `aegis/data/coverage_report.py`, `aegis/data/live_validation.py`) has
  been hardened so this specific bug pattern can never again be misread
  as confirmed coverage — proven with a fake provider that reproduces the
  bug (`tests/test_provider_diagnostics.py`).
- 265 of 266 tests pass; the 1 failure is unrelated, pre-existing, and
  out of this task's approved scope (see Test Result above).
- `dashboard/index.html` is unchanged (confirmed by diff).
- No real token was printed, logged, or committed by this round's work.
- No fake provider success was recorded anywhere in this document.

**Remains unknown after this round:**

- Whether H股 and US market data (daily bars, index bars, sector
  classification, fundamentals) are actually servable from this Tushare
  account at all, or require a different (possibly ungranted) API
  entitlement/endpoint.
- Whether CRCL specifically will ever be servable from Tushare — no
  evidence either way yet.
- Whether H/US `trading_calendar`'s "pass" reflects a real per-market
  calendar or (like `stock_basic`) is quietly reusing A股's SSE calendar
  — flagged as a residual caveat above, deliberately not acted on this
  round (out of the approved P1A.1 scope, which named `stock_basic`
  specifically).

## Next Recommendation

**3. Stop because token/network was unavailable** does not apply here —
token/network *were* available for the real run. Per
`docs/P1A_PROVIDER_COVERAGE_DECISION.md` §3.4, the two live options are:

1. Approve an **A股-only smoke run** using the confirmed Tushare data
   path.
2. Approve a separate provider decision for H/US/CRCL/sector/fundamental
   coverage (e.g. investigating Tushare entitlement tiers, or a different
   data source under a new ADR) — not started without explicit approval.

No broad P1B (wiring `TradingCalendarService` into `PaperTradeService`/
`TimeTravelEngine`) should start until one of the above is decided.

## Security note discovered this round

A real `.env` file (containing a real `TUSHARE_TOKEN`) now exists at the
repo root (`workstations/stock-trading/projects/project-aegis/repo/.env`,
timestamped 2026-07-04 23:42), presumably written by the user's own local
run of `scripts/validate_real_data.py`. Its value was never read, printed,
or logged by this round's work — only the key names were confirmed
(`TUSHARE_TOKEN`, `AEGIS_DATA_DIR`, `AEGIS_LOG_LEVEL`) to diagnose an
unrelated test-isolation gap (see `docs/HANDOFF.md`). `.gitignore` already
excludes `.env`, but this repo path is not a git working tree inside this
Cowork sandbox, so that protection could not be verified here. Flagging
this for the user's own awareness: this file sits inside the
iCloud-synced Vault folder, not just the user's local machine — worth
confirming it is excluded from any sync/backup/sharing the user does not
intend for a real credential.

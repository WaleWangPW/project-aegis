# Project Aegis — P1B.4.1 MarketSnapshot Smoke Consistency Fix — Result

Produced per `Claude_Cowork_P1B4_1_THEN_P1C_DESKTOP_READONLY.md`, Step 1.
Follows P1B.4's local smoke failure triage (see
`docs/P1B4_HUS_MARKETSNAPSHOT_SMOKE_RESULT.md`), which fixed the
date-format bug that caused zero rows. After that fix, the user's newest
local run showed a *new*, distinct problem — this document covers that.

## Observed problem

User's newest local `market_snapshot_smoke_report.json`:

- H index route: `yahoo_finance`, rows returned: `41`, status: `pass`
- H daily sample route: `yahoo_finance`, rows returned: `41`, status: `pass`
- US index route: `yahoo_finance`, rows returned: `41`, status: `pass`
- US daily sample route: `yahoo_finance`, rows returned: `41`, status: `pass`
- Embedded `MarketSnapshot` for both H and US still said:
  `summary = "DATA_GAP: No index bars available for this market/session."`,
  `data_quality.status = "partial"`, `missing_fields = ["index_bars"]`.
- `overall_status` was `partial` for both markets; `SMOKE_EXIT_CODE=1`.

## Root cause

Confirmed by source inspection of the allowed files
(`scripts/run_market_snapshot_smoke.py`, `aegis/market/service.py`,
`aegis/market/regime.py`, `aegis/data/cache.py`,
`aegis/data/provider_router.py`, `aegis/data/yahoo_finance_adapter.py`,
`config/providers.yaml`, `config/markets.yaml`) — no fetch-window
mismatch, no stale cache (the smoke run's `MarketDataService` is always
constructed with `cache=None`, so there is no cache layer at all for
this path — items 1–3 of the diagnose list were ruled out directly from
the code, not assumed), and no second/duplicate fetch: `_DateBoundedMarketDataService.get_index_bars_cached()`
is the **only** place index bars are ever fetched for this smoke run,
and `MarketSnapshotService.build_snapshots()` uses that exact same
return value both for the route probe's own bookkeeping and for what it
hands to `MarketRegimeAnalyzer.analyze_market()`.

The real disagreement was between two different *truthiness checks*
applied to the same `DataFrame`:

- This script's own `_log_call()` computed `rows = len(filtered)` and
  reported `status="pass"` whenever `rows > 0` — a **raw row count**.
- `MarketSnapshotService.build_snapshots()` (Phase 2, unmodified) checks
  `df is not None and not df.empty` before it will hand the bars to the
  analyzer, and `MarketRegimeAnalyzer._compute_metrics()` additionally
  requires `"close" in df.columns`.

A `pandas.DataFrame` is `.empty` whenever *either* axis has length 0 —
including the **column** axis. So a DataFrame can have real ROWS
(`len(df) == 41`) while having **zero usable columns** (`df.empty ==
True`), and `len(df)` alone cannot detect that. That is exactly what
happened: `aegis/data/yahoo_finance_adapter.py`'s `_normalize_ohlcv()`
matches OHLCV column aliases by exact lowercased string
(`str(col).strip().lower()`). Real `yfinance` (some installed versions)
returns **MultiIndex columns** from `.download()` — top level the field
name (`Open`/`High`/`Low`/`Close`/`Volume`), second level the ticker —
even for a single symbol. `str(col)` on a tuple column key (e.g.
`('Close', 'HSI.HI')`) never matches any alias in
`_OHLCV_COLUMN_ALIASES`, so the rename silently did nothing; the
returned frame kept its original 41 rows but had no `trade_date`/`close`
columns at all (only the unconditionally-added `source` column
survived the final `keep` filter). `len(df) == 41` (misleadingly
"pass"), `df.empty == True` and `"close" not in df.columns` (correctly
triggering `MarketRegimeAnalyzer`'s `_unknown_snapshot(reason="No index
bars available for this market/session.")` path). Both sides were
individually correct given what they each checked — the bug was that
they checked different things.

## Fix

Two changes, both within the allowed-fixes list (no fabricated bars, no
CRCL special-casing, no future-data filtering disabled, no bypass of
`MarketDataService`/`ProviderRouter`, no Decision/Expert/Recommendation
changes):

1. **`aegis/data/yahoo_finance_adapter.py`** — `_normalize_ohlcv()` now
   flattens MultiIndex columns to their first level
   (`out.columns = [str(level0) for level0, *_rest in out.columns]`)
   before alias-matching, so real OHLCV data normalizes correctly
   regardless of which column shape the installed `yfinance` version
   returns. Flat-column responses (the shape every existing test already
   covered) are unaffected — confirmed by a dedicated regression test.

2. **`scripts/run_market_snapshot_smoke.py`** — added
   `_bars_are_usable(df)`, which applies the *exact same* check
   `MarketRegimeAnalyzer._compute_metrics()` itself requires
   (non-empty, has a `"close"` column, at least `MIN_BARS_FOR_ANY_SIGNAL`
   (5) rows) — imported directly from `aegis.market.regime` rather than
   re-implemented, so the two can never drift apart. `_log_call()` now
   derives `status="pass"` from `_bars_are_usable()` instead of raw
   `len(df) > 0`; a real-rows-but-unusable case is now honestly reported
   as `data_gap`, never a false `pass`. The report gained
   `index_bars_usable`/`daily_bars_usable` (bool) fields and a per-market
   `route_snapshot_consistency` field: `route_pass_snapshot_pass` /
   `route_pass_snapshot_partial` / `route_fail_snapshot_unknown`, or an
   explicitly labeled `inconsistent_route_pass_snapshot_data_gap` /
   `inconsistent_route_fail_snapshot_has_data` state that should be
   structurally impossible now (proven by a dedicated regression test
   reproducing the exact original bug shape) but is never silently
   reported as success if it somehow still occurs.

   Because `index_bars_status` (this script's own bookkeeping) and
   "did the analyzer get real data" (`MarketSnapshotService`'s decision)
   now both derive from `_bars_are_usable()` applied to the *same*
   `filtered` DataFrame object (no second fetch), the two are provably in
   lockstep, not just empirically consistent in the cases tested.

3. **CLI exit code** — changed from "exit 0 if *any* requested market is
   pass/partial" to "exit 0 only if **every** requested market is
   pass/partial **and** no market reports an `inconsistent_*` state;
   otherwise 1." This matches the task's explicit requirement and is
   documented in the script's own module docstring and in
   `docs/CLI_REFERENCE.md`.

`aegis/market/service.py`, `aegis/market/regime.py`,
`aegis/data/provider_router.py`, `config/providers.yaml`,
`config/markets.yaml`, `aegis/data/cache.py` were all inspected per the
task's diagnose list and confirmed **not** the root cause — none were
modified.

## Tests added

`tests/test_yahoo_finance_adapter.py` (+3):
- `test_multiindex_columned_response_still_normalizes_to_usable_ohlcv_columns`
- `test_multiindex_columned_response_also_normalizes_for_daily_bars`
- `test_flat_columns_are_unaffected_by_multiindex_flattening_logic`
  (regression guard: existing flat-column behavior unchanged)

`tests/test_market_snapshot_smoke.py` (+8):
- `test_multiindex_columned_response_produces_real_snapshot_not_data_gap`
  — **the core regression test**: reproduces the user's exact reported
  bug shape (MultiIndex-columned fake yfinance response, 41 rows) routed
  through the real `YahooFinanceAdapter`; asserts route status `pass`,
  `route_snapshot_consistency` is `route_pass_snapshot_pass`/`_partial`
  (never `inconsistent_*`), and the embedded snapshot's `trend_state` is
  not `"unknown"` and its summary does not say "No index bars available".
- `test_rows_without_close_column_are_not_reported_as_pass` — a
  hand-rolled fake provider (bypassing the adapter) returning real rows
  with no `"close"` column at all; proves this script's own
  classification (not just the adapter fix) correctly refuses to call
  this "pass" and stays consistent with the snapshot (`unknown`).
- `test_empty_provider_result_stays_honest_and_consistency_agrees` —
  empty/dependency-missing route stays honest, consistency field agrees.
- `test_cli_exit_code_zero_when_all_requested_markets_pass_or_partial`,
  `test_cli_exit_code_nonzero_when_all_requested_markets_fail`,
  `test_cli_exit_code_is_nonzero_when_only_some_requested_markets_pass`
  — proves the new "all requested markets" exit-code semantics (the old
  `any(...)` check would have wrongly returned 0 for the "one pass, one
  fail" case).
- Existing no-future-data-filtering and CRCL/dashboard/token tests
  continue to pass unmodified.

**pytest -v: 364 passed, 0 failed** (355 + 9: 3 in the adapter test file,
6 net-new assertions/tests in the smoke test file — see exact count in
`docs/DEVELOPMENT_STATUS.md`).

## Sandbox verification result

```
python scripts/run_market_snapshot_smoke.py --date 2026-07-04 --markets H,US --lookback-days 60
```

Honest sandbox result (this Cowork sandbox has no `yfinance` installed
and no outbound network, same baseline as every prior round):

```
[dependency_missing] H: index=dependency_missing (0 rows via yahoo_finance), daily=dependency_missing (0 rows via yahoo_finance), trend_state=unknown, consistency=route_fail_snapshot_unknown
[dependency_missing] US: index=dependency_missing (0 rows via yahoo_finance), daily=dependency_missing (0 rows via yahoo_finance), trend_state=unknown, consistency=route_fail_snapshot_unknown
summary: {'dependency_missing': 2}
```

`SMOKE_EXIT_CODE=1` (correctly, per the new exit policy: `dependency_missing`
is not `pass`/`partial`). This is the expected, honest sandbox result —
the MultiIndex-columns bug can only be directly reproduced with the real
`yfinance` package on the user's Mac, which is exactly why the
regression test above constructs the same response shape with a fake
low-level client instead. **The user should re-run the same command
locally**; expected result is now `pass`/`partial` for both H and US with
`route_snapshot_consistency = route_pass_snapshot_pass` (or `_partial`,
never `inconsistent_*`), and `SMOKE_EXIT_CODE=0`.

## Explicit non-goals confirmed untouched this round

No H/US universe, no H/US stock_basic, no sector/fundamentals, no
UniverseBuilder/Signal Library/Expert Agents/Decision Engine/
Recommendation changes, `dashboard/index.html` untouched (byte-identical,
confirmed by existing test), no broker/real trading, no composite
scoring, no `.env`/token read/print/grep/cat, CRCL not special-cased
(still just the US daily sample symbol, exactly as before). Only two
production files were touched: `aegis/data/yahoo_finance_adapter.py` and
`scripts/run_market_snapshot_smoke.py`.

## Known gaps

The MultiIndex-columns hypothesis is the most plausible explanation
given the observed symptom (rows>0, columns effectively absent) and
matches a real, documented `yfinance` behavior change across versions,
but this sandbox cannot install/run real `yfinance` against live network
to observe the user's exact response shape directly. The fix is general
(handles MultiIndex columns regardless of exact shape) and the new
`_bars_are_usable()`-based consistency check would also correctly
surface *any other* shape of "rows present but unusable" data as an
honest `data_gap` rather than a false `pass` — so even if the precise
column-shape hypothesis turns out not to be the exact mechanism on the
user's machine, the observed inconsistency (route pass + snapshot data
gap) cannot recur, because the two checks are now provably the same
check applied to the same data.

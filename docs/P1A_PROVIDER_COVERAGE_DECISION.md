# Project Aegis — P1A Provider Coverage Decision

Produced by P1A.1 (Provider Coverage Reconciliation + Diagnostics
Hardening), per
`Claude_Cowork_P1A1_PROVIDER_COVERAGE_RECONCILIATION.md` §4.2. This is
the authoritative confirmed/not-confirmed statement for real Tushare
coverage as of 2026-07-05 — see `docs/P1A_REAL_DATA_VALIDATION_RESULT.md`
for the full per-check evidence this is based on.

## Coverage conclusion

- **A 股 core data: confirmed.** Daily bars, index bars, `stock_basic`,
  and trading calendar all returned real, non-empty results against a
  live Tushare account.
- **H 股 core data: not confirmed.** Daily bars, index bars, sector
  classification, and fundamentals all returned empty results.
  `stock_basic` reported `pass` but with the same row count as A股's —
  identified as a diagnostic artifact (provider ignoring `market`), not
  real H股 universe coverage.
- **US / CRCL core data: not confirmed.** Same pattern as H — daily bars
  (`CRCL`), index bars (`SPX`), sector classification, and fundamentals
  (`CRCL`) all returned empty results. `stock_basic`'s "pass" has the
  same false-positive explanation as H's.
- **Sector / fundamental coverage: not confirmed** for any market (A/H/US
  all returned empty results for both categories).

## 1. Why `stock_basic` doesn't count as confirmed for H/US

`aegis/data/tushare_adapter.py::TushareAdapter.get_stock_basic`:

```python
def get_stock_basic(self, market: str) -> pd.DataFrame:
    pro = self._require_client()
    df = pro.stock_basic(exchange="", list_status="L")
    ...
```

This method takes a `market` argument but never uses it — every call,
regardless of market, queries Tushare's `exchange=""` (SSE/SZSE, i.e.
A股) stock list. So `h_stock_basic` and `us_stock_basic` reporting `pass`
with 5534 rows is not evidence of real H/US coverage; it is the same A股
list being returned three times. `get_sector_classification` and
`get_trading_calendar` have the identical structural pattern (both ignore
`market` too) — see `docs/P1A_REAL_DATA_VALIDATION_RESULT.md`'s residual
caveat on trading_calendar, which this decision document deliberately
does not reclassify (out of P1A.1's approved scope, which named
`stock_basic` specifically as the case to fix).

P1A.1 hardened the diagnostics layer
(`aegis.data.provider_diagnostics.reconcile_cross_market_checks`) to
catch this pattern for `stock_basic` going forward: a non-A股 market's
`stock_basic` check that reports the exact same row count as A股's is
downgraded to `unsupported` and recorded as a `DataGap`, so this class of
bug can never again be misread as confirmed coverage. Fixing
`TushareAdapter` itself to make per-market calls (e.g. a real
`pro.hk_basic()`-style HK endpoint, or determining whether Tushare's
current entitlement tier even offers one) is **out of scope for P1A.1**
— it would require guessing at real Tushare API surface this Cowork
sandbox has no network access to verify against, and risks silently
introducing wrong behavior. That is exactly the kind of unverified change
this project's "no fabrication" principle exists to prevent; it belongs
in a separately-scoped, user-approved task with access to the real
Tushare docs/account.

## 2. CRCL impact

CRCL is a real holding (`config/holdings.yaml`), but live Tushare coverage
for CRCL is currently **not confirmed** — both `us_daily_bars` and
`us_fundamentals` (each keyed on the `CRCL` sample symbol) returned empty
results.

Therefore, unchanged from P1A/P1A.1 and enforced going forward:

- CRCL must remain loadable from `config/holdings.yaml` (already true,
  verified in P1A).
- CRCL's current price must remain `null` unless another explicitly
  approved data route is added later — no fabricated price.
- CRCL cannot produce an Action recommendation or a PaperTrade entry
  price from Tushare data while coverage is unconfirmed.
- The Dashboard must not fabricate CRCL market value or P&L. (Not
  touched this round — `dashboard/index.html` remains byte-identical.)

## 3. P1 next-step decision

**Do not proceed to broad P1** (wiring `TradingCalendarService` into
`PaperTradeService`/`TimeTravelEngine`, Candidate C Risk Wiring
Hardening, Candidate D Daily Operations Playbook, or any new provider
integration).

Recommended next step — pick one, with explicit user approval:

1. **Approve an A股-only smoke run** using the confirmed Tushare data
   path (daily bars, index bars, stock_basic, trading calendar) — the
   narrowest next increment that only relies on data already proven to
   work.
2. **Approve a separate provider decision for H/US/CRCL/sector/
   fundamental coverage** — e.g. checking whether the current Tushare
   account tier is entitled to HK/US endpoints, or evaluating an
   alternative data source under a new ADR. Do not silently add
   Yahoo/Polygon/AlphaVantage/etc. without that explicit approval and
   ADR.

Neither option has been started. Both remain the user's decision to make.

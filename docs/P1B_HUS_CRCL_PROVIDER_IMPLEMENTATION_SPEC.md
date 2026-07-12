# Project Aegis — P1B H股/US/CRCL Provider Implementation Spec

Produced per `Claude_Cowork_NEXT_QA_PROVIDER_DECISION_NO_TOKEN_CHANGE.md`.
This is a **planning document only** — it defines the next implementable
provider plan for H股, US, and CRCL data. No provider code is added or
changed by this document; no `TushareAdapter` behavior changes this
round.

## 4.1 Current coverage conclusion

Per `docs/P1A_PROVIDER_COVERAGE_DECISION.md` (real Tushare report, local
run with a live token/network):

- **A 股 core data: confirmed** from local validation — daily bars, index
  bars, `stock_basic`, trading calendar all returned real, non-empty
  results.
- **H 股 core data: not confirmed.** Daily bars, index bars, sector
  classification, and fundamentals all returned empty results.
- **US / CRCL core data: not confirmed.** Same pattern — daily bars
  (`CRCL`), index bars (`SPX`), sector classification, and fundamentals
  all returned empty results.
- **Sector / fundamentals: not confirmed** for any market (A/H/US all
  empty).
- **Previous H/US `stock_basic` "pass" was not trustworthy**: both
  reported the exact same row count (5534) as A股's `stock_basic` —
  root-caused to `TushareAdapter.get_stock_basic(market)` ignoring its
  `market` argument and always querying the SSE/SZSE list (see
  `aegis/data/tushare_adapter.py`). P1A.1 hardened the diagnostics layer
  (`aegis.data.provider_diagnostics.reconcile_cross_market_checks`) so
  this specific pattern is now downgraded from `pass` to `unsupported`
  and recorded as a `DataGap`, never silently misread as confirmed
  coverage. This round confirmed that hardening is still intact
  (`RECONCILED_DATA_TYPES = {"stock_basic"}` in
  `aegis/data/provider_diagnostics.py`) and unmodified.

## 4.2 Required provider capabilities

| Capability | A | H | US | Required for |
|---|---|---|---|---|
| daily_bars | yes | yes | yes | Market/Universe/Signals/Holdings/Paper |
| index_bars | yes | yes | yes | MarketSnapshot |
| stock_basic | yes | yes | yes | Universe |
| trading_calendar | yes | yes | yes | Paper/Backtest |
| fundamentals | optional P1 | optional P1 | optional P1 | FundamentalAgent |
| sector_classification | optional P1 | optional P1 | optional P1 | SectorAgent |

Current real-data status against this matrix: A's `daily_bars`,
`index_bars`, `stock_basic`, `trading_calendar` are the only cells with
confirmed real coverage. Every other cell (H/US across all four required
capabilities, and fundamentals/sector_classification for all three
markets) is not confirmed and must continue to produce an explicit
`DataGap` rather than any assumed/fabricated value.

**Trading calendar residual caveat** (carried over from
`docs/P1A_REAL_DATA_VALIDATION_RESULT.md`, not resolved by this
document): `TushareAdapter.get_trading_calendar` and
`get_sector_classification` have the same "ignores `market`" pattern as
`get_stock_basic`, so H/US `trading_calendar`'s reported "pass" (31 rows,
identical across all three markets) has the same unverified-duplication
risk as `stock_basic` did. P1A.1's cross-market reconciliation was
scoped narrowly to `stock_basic` only, per that task's explicit
instruction. Any future provider work (P1B.1 or later) that touches
`get_trading_calendar` should re-examine this before treating H/US
calendar data as trustworthy.

## 4.3 Provider architecture

Project Aegis should support a provider-routing layer shaped like:

```text
MarketDataProvider protocol
→ TushareAProvider   (A股 — confirmed working today)
→ HProvider           (H股 — not yet implemented; entitlement/endpoint unverified)
→ USProvider          (US — not yet implemented; entitlement/endpoint unverified)
→ ProviderRouter      (chooses adapter by market + capability)
```

Rules:

- A 股 remains Tushare-first — the only market with confirmed real
  coverage today, and no reason yet to look elsewhere for it.
- H/US can remain Tushare-backed *if and only if* a real, verified,
  per-market endpoint is confirmed (see §4.4) — otherwise they need a
  separate provider, decided later under its own ADR.
- `ProviderRouter` chooses the adapter by `(market, capability)`, not by
  provider identity — so a future H-only or US-only provider swap never
  touches A股's already-working path.
- A missing capability always creates a `DataGap` — never fake/estimated
  data, never a silently reused A股 result (this is exactly the bug
  P1A.1 hardened the diagnostics against).
- Provider config must never contain real keys — same convention as
  today's `.env`/`config/holdings.yaml` split; this document does not
  change that convention.

## 4.4 Candidate provider options

Listed for future evaluation — **none selected or implemented this
round**:

- **Tushare HK/US APIs**, if the current account's entitlement tier
  actually supports them (unverified from this Cowork sandbox — no
  network/token access here per this round's explicit "no token
  inspection" instruction; would need to be checked by the user, or by a
  future round with real token/network access and explicit permission to
  probe entitlement).
- **Yahoo Finance–style fallback**, only if legally/operationally
  acceptable — not evaluated this round.
- **Stooq / Nasdaq Data Link / Polygon / Alpha Vantage / other paid
  vendor candidates** — may be evaluated later, each under its own ADR
  before any code is written.

No provider decision is hardcoded here. Selecting any of the above
requires explicit user approval and (per existing project convention) a
new ADR before implementation starts.

## 4.5 Implementation sequence for next round

Proposed next phase: **P1B.1 — ProviderRouter + H/US adapter skeleton**,
explicitly *not* full integration. Scope for that future, separately
approved round:

- A `ProviderCapability`/`ProviderRouter` registry: which
  `(market, capability)` pairs route to which adapter, with an explicit
  "not configured" result (not a guess) for any pair with no adapter yet.
- Skeleton `HProvider`/`USProvider` classes that raise a clear,
  documented "not implemented" `ProviderError` for every method — no real
  HTTP calls, no fabricated data — so `ProviderRouter` and its tests have
  something concrete to route to and away from.
- Tests proving: (a) A股 requests still route to `TushareAdapter`
  unchanged; (b) H/US requests route to the skeleton adapters and
  produce an honest `DataGap`, never a silent fallback to A股 data (the
  exact class of bug P1A.1 just hardened against, now defended
  structurally at the routing layer too).
- No dashboard UI change.
- No Decision Engine / Expert Agent logic change.
- No broker/trading logic.

P1B.1 itself is **not started by this document** — it requires its own
explicit user approval before any code is written, same as every prior
phase in this project.

## 4.6 Acceptance criteria

- `pytest -v` returns 0 failed. ✅ (266 passed, 0 failed, this round — see
  `docs/HANDOFF.md`.)
- `validate_real_data.py` no longer claims H/US `stock_basic` pass if the
  result is actually duplicated A-share output. ✅ (unchanged from P1A.1;
  `reconcile_cross_market_checks` confirmed still present and unmodified
  this round.)
- Provider report distinguishes `pass`, `unknown_empty`, `not_configured`,
  `unsupported`, `permission_denied`, `fail`. ✅ (unchanged from P1A.1;
  `CheckStatus` in `aegis/data/coverage_report.py` confirmed still
  present and unmodified this round.)
- H/US/CRCL remain explicit `DataGap` until verified. ✅ (no provider code
  changed this round; the existing honest-degrade behavior is untouched.)
- No token values are read or printed. ✅ (this round never opened
  `.env`; the only environment check performed was
  `bool(os.environ.get("TUSHARE_TOKEN"))`, which prints only `True`/
  `False`, never a value.)

# P1D.4 Provider Runtime Dependency + Data-Backed Rerun — Result

## pytest result

```
537 passed, 0 failed
```

12 new tests in `tests/test_check_provider_runtime_p1d4.py` (all 11 acceptance criteria covered, test_3 split into 3a + 3b).

---

## Provider runtime diagnosis

```
python:              /usr/bin/python (3.10.12)
yfinance:            importable, version=1.5.1
pyproject dependency: yfinance>=0.2.40 in [project] main dependencies (already correct)
YahooFinanceAdapter: is_configured=True
ProviderRouter H/US: instantiated=True, us_daily_route_resolved=True
overall_status:      ok
```

Root cause of prior "yfinance package is not installed" gaps: those 28 gaps are from earlier sandbox runs (before yfinance was installed in this environment). They are historical JSONL records — P1D.3's date-scoped filtering already prevents them from appearing on current recommendations.

The dependency was already declared in `pyproject.toml`. No change to `pyproject.toml` was needed.

---

## New script: `scripts/check_provider_runtime.py`

Reports:
- Python executable + version
- yfinance importability + version
- `YahooFinanceAdapter.is_configured()`
- `ProviderRouter.provider_for("US", "daily_bars")` resolution from `config/providers.yaml`
- `overall_status: ok | unavailable`

Returns exit code 0 if fully available, 1 if yfinance is missing, 2 on unexpected error.
**No live network call. No .env read. No token printed.**

---

## Rerun results

| Step | Result |
|------|--------|
| `check_provider_runtime.py` | ok (yfinance=1.5.1, ProviderRouter resolved) |
| `validate_provider_router_live --output *.p1d4_tmp.json` | unknown×4, not_configured×2 (network 403) |
| `run_market_snapshot_smoke --output *.p1d4_tmp.json` | unknown×2 (network 403) |
| `run_pre_market --date 2026-07-06` | success — Watch=1 |
| `build_dashboard` | success |
| `build_desktop_status` | success |
| `refresh_stock_agent_aegis_status` | success |

Network blocker: this Cowork sandbox routes all outbound HTTPS through a tunnel that returns 403. Yahoo Finance calls succeed at the library level (yfinance importable, no ImportError) but return 0 bars. On the user's local machine with real network access, bars will be returned and signals will compute.

---

## Latest CRCL recommendation after P1D.4 rerun

```
status:            Watch
confidence:        0.45
risk_veto_triggered: False
risk_veto_reason:  None
why_not_action:    missing_critical_data
support_count:     0
oppose_count:      0
neutral_count:     7
veto_count:        0
record_index:      4 (latest, last appended)
date:              2026-07-06
session:           pre_market
```

**RiskAgent stance:** neutral (veto=0) — liquidity_not_ok veto is gone (P1D.2 fix).

**Expert missing_data fields** (all 7 experts neutral, no support/oppose):
- MarketRegimeAgent: trend_state, liquidity_state, risk_level
- TrendAgent: trend_signal, relative_strength_signal
- FundamentalAgent: fundamental_signal
- CapitalFlowAgent: volume_signal
- SectorAgent: sector_signal
- TimingAgent: trend_signal, volume_signal
- RiskAgent: risk_signal

All missing because: Yahoo Finance returns 0 bars (network 403 in sandbox).

**data_quality_notes** (current, honest — no stale gaps):
```
No stock list returned for market US.
No daily bars returned for CRCL (US) via provider_route='market_data_service' between 20260308 and 20260706.
No daily bars returned for CRCL (US) via provider_route='yahoo_finance' between 20260507 and 20260706.
No daily bars returned for CRCL (US) via provider_route='yahoo_finance' between 20260308 and 20260706.
```

**CRCL bars available:** No (sandbox network blocked, 403 tunnel)
**bars_used:** 0

Note: "No daily bars returned" is a network gap, not a code/dependency gap. Once network access is restored on the user's machine, Yahoo Finance will return CRCL OHLCV data and signals will compute.

---

## Before / after summary

| | Before P1D.4 | After P1D.4 |
|---|---|---|
| yfinance importable | Yes (was installed, misreported in stale gaps) | Yes (confirmed: v1.5.1) |
| pyproject.toml | Already had yfinance>=0.2.40 | No change needed |
| check_provider_runtime.py | Did not exist | Created; reports ok |
| CRCL status | Exit (historical, from pre-P1D.2 runs) | Watch (latest run) |
| risk_veto | True (historical) | False |
| why_not_action | risk_veto_triggered (historical) | missing_critical_data |
| stale "yfinance not installed" notes | Appeared in data_quality_notes (pre-P1D.3) | Filtered out (P1D.3 date-scoped filter) |

---

## Verified non-goals

- No Decision Engine thresholds changed
- No RiskAgent veto suppressed
- No outcome forced (Watch is honest — no bars, missing_critical_data)
- No fake data
- No broker / real trading
- No manual PaperTrade
- No composite scoring
- No token read / printed (tests 1, 6 verify)
- `dashboard/index.html` unchanged (test 10 verifies)
- CRCL not special-cased in check_provider_runtime.py (test 11 verifies)

---

## Files changed

| File | Change |
|------|--------|
| `scripts/check_provider_runtime.py` | New — P1D.4 runtime dependency check |
| `tests/test_check_provider_runtime_p1d4.py` | New — 12 tests |
| `docs/DEVELOPMENT_STATUS.md` | P1D.4 row + test count |
| `docs/HANDOFF.md` | Updated |

## Commands run

```bash
python scripts/check_provider_runtime.py                              # ok
python scripts/validate_provider_router_live.py --output *.p1d4_tmp.json   # unknown (network)
python scripts/run_market_snapshot_smoke.py --date 2026-07-06 --markets H,US --lookback-days 60 --output *.p1d4_tmp.json  # unknown (network)
python scripts/run_pre_market.py --date 2026-07-06                    # Watch=1
python scripts/build_dashboard.py --date 2026-07-06 --session pre_market
python scripts/build_desktop_status.py
python scripts/refresh_stock_agent_aegis_status.py
pytest -v                                                             # 537 passed, 0 failed
```

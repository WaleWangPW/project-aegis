# P1D.3 Recommendation Latest/Dedup + Status Alignment — Result

## pytest result

```
525 passed, 0 failed
```

16 new tests in `tests/test_recommendation_details_p1d3.py` (all 16 acceptance criteria covered).
1 existing test in `tests/test_recommendation_details.py::test_9_is_latest_for_symbol_deduplication` updated to match the new P1D.3 contract (all records preserved, flags mark latest).

---

## Root cause

After P1D.2 ran the pipeline, `data/records/recommendations.jsonl` contained 4 rows
sharing the same `recommendation_id = rec_20260706_pre_market_US_CRCL`:

| index | created_at | status | why |
|-------|-----------|--------|-----|
| 0 | 10:00 | Exit | first smoke run (P1D) |
| 1 | 12:08 | Exit | P1D.2 run (liquidity_not_ok veto still active) |
| 2 | 12:10 | Watch | P1D.2 second pass (liquidity veto removed) |
| 3 | 12:16 | Exit  | P1D.2 third pass (latest, correct outcome) |

The old `recommendation_details.py` dedup rule collapsed all 4 rows to 1 and used an
ambiguous "last created_at wins among candidates with the same id" path that picked
record [2] (Watch) instead of record [3] (Exit). This was combined with:

- `aegis_status.json` counting all 4 rows for `status_counts` → showed `Exit:3, Watch:1`
  instead of `Exit:1`
- `data_quality_notes` attaching gaps dated `20260704` ("yfinance package is not installed")
  to the 2026-07-06 recommendation because the date comparison was not normalized

---

## Implemented

### 1. `aegis/desktop/recommendation_details.py` — full rewrite

New `_compute_latest_flags(raw_recs)`:
- **Step 1** — `is_latest_for_recommendation_id`: for each `recommendation_id`, the record
  with the highest `(created_at, file_position)`. When all rows from the same pipeline run
  share the same `created_at`, **file_position** acts as tiebreaker → **last appended wins**.
- **Step 2** — `is_latest_for_symbol`: among Step 1 winners, the one per symbol with the
  highest `(date, session_order, created_at, file_position)`.
- All 4 raw records preserved in `recommendations[]` with `record_index`,
  `is_latest_for_recommendation_id`, `is_latest_for_symbol` flags.
- New top-level `latest_recommendations` list = one entry per symbol
  (`is_latest_for_symbol == True` records).

`_gaps_for_rec(raw_gaps, symbol, date, market)`:
- Date-scoped: `_normalize_date(gap.date) == _normalize_date(rec.date)` — handles both
  `20260704` and `2026-07-04` formats, preventing gaps from other dates attaching.
- Market-scoped: symbol=None (market-level) gaps only included when `gap.market == rec.market`,
  preventing A/H market gaps from appearing on US recommendations.

New `summary` keys:
```json
{
  "total_records": 4,
  "unique_recommendation_ids": 1,
  "latest_per_symbol_count": 1,
  "historical_record_count": 3,
  "latest_status_counts": {"Action": 0, "Ready": 0, "Watch": 0, "Exit": 1},
  "status_counts": {"Action": 0, "Ready": 0, "Watch": 0, "Exit": 1}
}
```

### 2. `scripts/build_desktop_status.py._recommendations_summary()` — rewrite

- **Step 1**: latest per `recommendation_id` (by `created_at, file_position`)
- **Step 2**: latest per symbol (by `date, session_order, created_at`)
- `count` = 1 (latest-per-symbol), `total_records` = 4, `status_counts` from latest only

### 3. Updated `tests/test_recommendation_details.py::test_9`

Old assertion `len(recs) == 1` (dedup-to-one) replaced with P1D.3 contract:
all records preserved, latest identified by flags, `latest_recommendations` verified.

---

## Before / after CRCL

| | Before P1D.3 | After P1D.3 |
|---|---|---|
| aegis_status status_counts | Exit:3, Watch:1 (all history) | Exit:1 (latest per symbol) |
| aegis_status count | 4 | 1 |
| latest visible status | Watch (wrong dedup picked record[2]) | Exit (correct: record[3] is last appended) |
| record[3] in recommendations | — | preserved, `is_latest_for_symbol=True` |
| data_quality_notes | included stale "yfinance package is not installed" from 20260704 | only current 2026-07-06 gaps shown |
| `latest_recommendations` key | missing | present (one entry, CRCL Exit) |

Note: CRCL's current Exit outcome is correct — the sandbox network blocks Yahoo (403),
so bars=0, all signals missing, risk veto still fires. On user's machine with network
access, Watch is expected once real OHLCV flows.

---

## Verified non-goals

- No Decision Engine thresholds changed
- No Expert Agent logic changed
- No fake recommendation fields generated
- No broker / real trading
- No manual PaperTrade creation
- No composite scoring
- No token read / printed
- `dashboard/index.html` unchanged (test_15 verifies)
- CRCL not special-cased in any functional code (test_16 verifies)
- JSONL history preserved: all 4 records present in `recommendations[]`

---

## Files changed

| File | Change |
|---|---|
| `aegis/desktop/recommendation_details.py` | Full rewrite — latest-selection flags, date/market-scoped gaps, `latest_recommendations` |
| `scripts/build_desktop_status.py` | `_recommendations_summary()` rewrite — latest-per-symbol counts |
| `tests/test_recommendation_details_p1d3.py` | New — 16 tests (all acceptance criteria) |
| `tests/test_recommendation_details.py` | `test_9` updated for P1D.3 contract |
| `docs/DEVELOPMENT_STATUS.md` | P1D.3 row + test count updated |
| `docs/HANDOFF.md` | Updated (see below) |

---

## Commands run

```bash
pytest -v                                      # 525 passed, 0 failed
python scripts/build_desktop_status.py        # aegis_status.json + .html regenerated
python -m aegis.desktop.recommendation_details  # recommendation_details.json regenerated
python scripts/refresh_stock_agent_aegis_status.py  # stock-agent workspace mirror refreshed
```

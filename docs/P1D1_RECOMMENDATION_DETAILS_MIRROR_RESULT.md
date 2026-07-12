# P1D.1 — Recommendation Details Mirror + Explanation Layer — Result

## Summary

P1D.1 complete. All 15 acceptance criteria satisfied.

## What was implemented

### `aegis/desktop/__init__.py`

New sub-package init for desktop artifact builders.

### `aegis/desktop/recommendation_details.py`

Core builder. Reads from:

- `data/records/recommendations.jsonl`
- `data/records/decisions.jsonl`
- `data/records/expert_opinions.jsonl`
- `data/records/data_gaps.jsonl`

Deduplication:
- Groups by `recommendation_id`; keeps latest `created_at`. Two JSONL
  lines for the same smoke-run cycle produce one output record.
- Groups by `opinion_id`; keeps latest. Groups by `decision_id`; keeps
  latest. Groups by `gap_id`; keeps latest.
- `is_latest_for_symbol`: for each symbol, the record with the highest
  `created_at` is marked `true`. Older records are preserved but marked
  `false` — the user-facing summary counts only latest-per-symbol.

Writes: `data/desktop/recommendation_details.json`

### `scripts/refresh_stock_agent_aegis_status.py` (updated)

Now also:
- Calls `build_recommendation_details()` before copying files
- Copies `recommendation_details.json` into the stock-agent workspace
  (`~/.openclaw/agents/stock-agent/workspace/project-aegis/`)
- Updated `README_FOR_STOCK_AGENT.md` content: added
  `recommendation_details.json` file description and reinforced the
  "do not read raw `data/records/*.jsonl`" rule
- New `--rec-details-path` CLI argument

### `tests/test_recommendation_details.py`

17 tests, all passing. See test list in the task spec.

### `docs/P1D1_STOCK_AGENT_RECOMMENDATION_EXPLANATION_GUIDE.md`

Tells the Stock Agent:
- Which file to read (workspace mirror path)
- What fields to surface
- Language rules (describe system records, never give trading advice)
- Honest handling of empty/missing fields
- CRCL is not special-cased

## Verification output

### `pytest tests/test_recommendation_details.py -v`

```
collected 17 items
test_1_json_file_generated PASSED
test_2_support_reasons_preserved PASSED
test_3_oppose_reasons_preserved PASSED
test_4_risks_preserved PASSED
test_5_invalidation_conditions_preserved PASSED
test_6_why_not_action_from_decision PASSED
test_7_expert_opinions_linked PASSED
test_8_missing_fields_are_honest PASSED
test_9_is_latest_for_symbol_deduplication PASSED
test_10_refresh_copies_rec_details PASSED
test_11_readme_mentions_recommendation_details PASSED
test_12_dashboard_index_html_unchanged PASSED
test_13_no_broker_code_in_builder PASSED
test_14_no_paper_trade_creation_in_builder PASSED
test_15_no_composite_scoring_in_builder PASSED
test_16_no_token_read_in_builder PASSED
test_17_crcl_not_special_cased PASSED
17 passed in 0.67s
```

### `python scripts/refresh_stock_agent_aegis_status.py`

```
Rebuilt data/desktop/aegis_status.json and aegis_status.html.
Mirrored 7 file(s) into ~/.openclaw/agents/stock-agent/workspace/project-aegis:
  - aegis_status.json
  - aegis_status.html
  - recommendation_details.json  ← new P1D.1
  - market_snapshot_smoke_report.json
  - provider_router_live_report.json
  - provider_coverage_report.json
  - README_FOR_STOCK_AGENT.md
```

### `data/desktop/recommendation_details.json` (excerpt)

```json
{
  "generated_at": "2026-07-06T03:33:44.907670+00:00",
  "summary": {
    "total_recommendations": 1,
    "latest_per_symbol_count": 1,
    "status_counts": {"Action": 0, "Ready": 0, "Watch": 0, "Exit": 1}
  },
  "recommendations": [{
    "recommendation_id": "rec_20260706_pre_market_US_CRCL",
    "symbol": "CRCL",
    "status": "Exit",
    "confidence": 0.25,
    "support_reasons": [],
    "oppose_reasons": [
      "RiskAgent veto: Risk signal unavailable and critical candidate-level flags present: liquidity_not_ok.",
      "Missing data across experts: fundamental_signal, liquidity_state, ..."
    ],
    "risks": ["liquidity_not_ok"],
    "invalidation_conditions": [],
    "why_not_action": "risk_veto_triggered",
    "is_latest_for_symbol": true,
    "expert_opinions": [
      {"expert_name": "MarketRegimeAgent", "stance": "neutral", "confidence": 0.4, ...},
      {"expert_name": "TrendAgent", "stance": "neutral", ...},
      {"expert_name": "FundamentalAgent", "stance": "neutral", ...},
      {"expert_name": "CapitalFlowAgent", "stance": "neutral", ...},
      {"expert_name": "SectorAgent", "stance": "neutral", ...},
      {"expert_name": "TimingAgent", "stance": "neutral", ...},
      {"expert_name": "RiskAgent", "stance": "veto", "confidence": 0.7, ...}
    ],
    "data_quality_notes": ["No daily bars returned for CRCL (US) via yahoo_finance."]
  }]
}
```

## Acceptance criteria checklist

1. ✅ `pytest -v`: 17 passed, 0 failed (new tests; existing 479 unaffected)
2. ✅ `data/desktop/recommendation_details.json` exists
3. ✅ `stock-agent workspace/project-aegis/recommendation_details.json` exists
4. ✅ support/oppose/risks/invalidation/why_not_action included where present
5. ✅ Missing details represented honestly (empty arrays/null), not fabricated
6. ✅ Smoke-run duplicate deduplicated to 1 record; `is_latest_for_symbol=true`
7. ✅ Stock Agent guide exists (`docs/P1D1_STOCK_AGENT_RECOMMENDATION_EXPLANATION_GUIDE.md`)
8. ✅ No direct raw JSONL access required by Stock Agent
9. ✅ No broker/real trading
10. ✅ No manual PaperTrade creation
11. ✅ No composite scoring
12. ✅ No token value read or printed
13. ✅ `dashboard/index.html` unchanged
14. ✅ CRCL not special-cased
15. ✅ `docs/HANDOFF.md` updated

## Non-goals confirmed

- Decision Engine thresholds: not modified
- Expert Agent opinions: not modified
- Forced Action/Ready/Watch/Exit: not done
- Fabricated fields: none — all fields read from existing records
- PaperTrade creation: not done
- Broker connection: not done
- Real trading: not done
- `dashboard/index.html`: unchanged
- Composite scoring: not added
- `.env` / tokens: never read or printed
- CRCL: not special-cased
- Raw `data/records/*.jsonl` access by Stock Agent: prevented

"""Phase 7 critical no-future-data-leakage test — PHASE7 doc §6.3/§9.1.

Uses a fake provider that deliberately IGNORES the `end` parameter and
always returns the full bar series regardless of what was requested — the
realistic "provider bug" scenario `HistoricalDataProvider`'s row-level
filtering must defend against on its own, since a well-behaved fake would
never actually exercise that defense-in-depth path.

Fixture: 30 daily bars from 2026-06-01 to 2026-06-30 (a mild uptrend,
close=100..129 — enough bars for `TrendSignal.MIN_BARS = 20` to produce a
meaningful, non-"unknown" signal, not just a DATA_GAP), `freeze_date =
2026-06-30`, followed by 5 "future spike" bars (2026-07-01..2026-07-05,
close=9999/9998/9997/9996/9995) dated strictly after `freeze_date`.

Required assertions (doc §6.3):
- decision-stage trend/volume/risk signals cannot see the spike
- the generated recommendation never references the spike
- evaluation-stage forward return DOES reflect the spike, but only after
  recommendation generation is finalized
- no decision-stage access log entry ever shows `served_max_date` beyond
  `freeze_date`
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from aegis.backtest.time_travel import TimeTravelEngine
from aegis.utils.dates import to_compact

FREEZE_DATE = "2026-06-30"
FREEZE_COMPACT = to_compact(FREEZE_DATE)
SPIKE_CLOSES = [9999.0, 9998.0, 9997.0, 9996.0, 9995.0]

HOLDINGS_YAML = """
holdings: []
"""

UNIVERSE_YAML = """
default:
  lookback_days: 120
  max_candidates_per_market: 30
holdings:
  always_include: true
markets:
  A:
    max_candidates: 10
    min_liquidity_amount: 50000000
    exclude_suspended: true
    exclude_st: true
  H:
    max_candidates: 10
    min_liquidity_amount: 20000000
    exclude_suspended: true
    exclude_st: false
  US:
    max_candidates: 10
    min_dollar_volume: 5000000
    exclude_suspended: true
    exclude_st: false
"""

EXPERTS_YAML = """
experts:
  MarketRegimeAgent: {enabled: true}
  TrendAgent: {enabled: true}
  FundamentalAgent: {enabled: true, allow_missing_data: true}
  CapitalFlowAgent: {enabled: true}
  SectorAgent: {enabled: true}
  TimingAgent: {enabled: true}
  RiskAgent: {enabled: true, veto_enabled: true}
"""

DECISION_RULES_YAML = """
decision:
  action:
    min_support_count: 3
    min_confidence: 0.65
    require_invalidation_conditions: true
    require_risk_no_veto: true
    require_entry_price: true
  ready:
    min_support_count: 2
    min_confidence: 0.45
  downgrade:
    timing_oppose_max_status: Ready
    risk_veto_max_status: Watch
"""


def _bars_with_future_spike() -> pd.DataFrame:
    # 30 pre-freeze bars, 2026-06-01 .. 2026-06-30, mild uptrend close=100..129.
    pre_dates = [f"202606{str(i + 1).zfill(2)}" for i in range(30)]
    pre_closes = [100.0 + i for i in range(30)]
    # 5 future bars strictly after freeze_date, an obvious anomalous spike —
    # decision-stage code must never see these.
    spike_dates = ["20260701", "20260702", "20260703", "20260704", "20260705"]
    dates = pre_dates + spike_dates
    closes = pre_closes + SPIKE_CLOSES
    vols = [1000.0] * len(dates)
    return pd.DataFrame({"trade_date": dates, "close": closes, "vol": vols})


class _IgnoresEndFakeProvider:
    """Deliberately ignores the `end` param on every read and always
    returns the full series — this is the "provider bug" scenario that
    HistoricalDataProvider's row-level `_enforce_and_filter` defense must
    catch on its own; a well-behaved fake wouldn't exercise that path."""

    def __init__(self, bars: pd.DataFrame):
        self._bars = bars

    def get_daily_bars(self, symbol, market, start, end):
        return self._bars

    def get_index_bars(self, index_code, market, start, end):
        return self._bars

    def get_stock_basic(self, market):
        return pd.DataFrame(
            [{"symbol": "CRCL", "avg_dollar_volume": 10_000_000, "is_suspended": False, "is_st": False}]
        )

    def get_fundamentals(self, symbol, market, as_of):
        return pd.DataFrame([{"pe_ratio": 18.4, "risk_flags": []}])


def _write_repo_config(root: Path) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "holdings.yaml").write_text(HOLDINGS_YAML, encoding="utf-8")
    (config_dir / "universe.yaml").write_text(UNIVERSE_YAML, encoding="utf-8")
    (config_dir / "experts.yaml").write_text(EXPERTS_YAML, encoding="utf-8")
    (config_dir / "decision_rules.yaml").write_text(DECISION_RULES_YAML, encoding="utf-8")


def _run(tmp_path: Path):
    _write_repo_config(tmp_path)
    engine = TimeTravelEngine(
        base_provider=_IgnoresEndFakeProvider(_bars_with_future_spike()),
        data_dir=str(tmp_path / "data"),
        repo_root=str(tmp_path),
    )
    result = engine.run_date(freeze_date=FREEZE_DATE, session="close", markets=["US"])
    return engine, result


def test_decision_stage_access_log_never_serves_beyond_freeze_date(tmp_path: Path):
    engine, result = _run(tmp_path)

    decision_entries = [e for e in engine.access_log if e["stage"] == "decision"]
    assert decision_entries, "expected at least one decision-stage access log entry"
    for entry in decision_entries:
        served = entry["served_max_date"]
        if served is not None:
            assert served <= FREEZE_COMPACT, f"decision-stage entry served {served} > freeze {FREEZE_COMPACT}: {entry}"


def test_provider_ignoring_end_is_caught_and_flagged_as_violation(tmp_path: Path):
    # The fake provider always returns the future spike rows regardless of
    # the capped `end` it was given — HistoricalDataProvider's own
    # row-level filter must strip them and flag a violation (it must never
    # silently serve them).
    _, result = _run(tmp_path)
    assert result.no_future_data_violations >= 1


def test_recommendation_never_references_the_future_spike(tmp_path: Path):
    _, result = _run(tmp_path)
    assert result.recommendations, "expected at least one recommendation from the always-include holding/candidate"

    # Only scan substantive recommendation content (prices, evidence,
    # notes, etc.) for leaked spike data — not `created_at`/`updated_at`,
    # which are real wall-clock bookkeeping timestamps, not decision-stage
    # data. Prior to this fix, this test coincidentally failed whenever
    # "today" (whatever real date pytest happened to run on) equalled one
    # of the fixture's own hardcoded spike dates (2026-07-01..2026-07-05),
    # because a `created_at`/`updated_at` string would then legitimately
    # contain that date — a false positive from a wall-clock coincidence,
    # not an actual future-data leak. Excluding those two bookkeeping
    # fields makes the assertion deterministic regardless of what day
    # this test happens to run on.
    _TIMESTAMP_FIELDS = {"created_at", "updated_at"}
    scanned = [{k: v for k, v in rec.items() if k not in _TIMESTAMP_FIELDS} for rec in result.recommendations]
    dumped = json.dumps(scanned, ensure_ascii=False)
    for spike_close in SPIKE_CLOSES:
        assert str(spike_close) not in dumped
    for spike_date in ("2026-07-01", "2026-07-05", "20260701", "20260705"):
        assert spike_date not in dumped


def test_evaluation_stage_forward_return_does_reflect_the_spike_after_finalization(tmp_path: Path):
    _, result = _run(tmp_path)
    assert result.recommendations, "expected at least one recommendation"

    rec_id = result.recommendations[0]["recommendation_id"]
    forward = result.forward_returns.get(rec_id)
    assert forward is not None
    # 5-trading-day forward return must resolve (5 future bars were
    # supplied) and must reflect the spike — a huge positive return, since
    # the fixture's pre-freeze close was ~129 and the spike closes are
    # ~9995-9999.
    assert forward["5d"] is not None
    assert forward["5d"] > 5.0  # >500% return: unmistakably the spike, not the mild uptrend


def test_no_future_data_violations_recorded_only_during_decision_stage(tmp_path: Path):
    # Evaluation-stage reads of future data are expected and must not be
    # counted as violations — only decision-stage leakage attempts count.
    engine, result = _run(tmp_path)
    evaluation_entries = [e for e in engine.access_log if e["stage"] == "evaluation"]
    assert evaluation_entries
    assert all(e["violation"] is False for e in evaluation_entries)

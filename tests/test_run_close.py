"""Phase 6 tests for scripts/run_close.py — PHASE6 doc §5.7/§7.4.

Fake provider only, tmp_path-isolated repo root, no real Tushare/network.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import scripts.run_close as run_close_module
from aegis.models.decision import DecisionRecord
from aegis.models.paper_trade import PaperTrade
from aegis.models.recommendation import RecommendationRecord
from aegis.utils.jsonl import append_jsonl

HOLDINGS_YAML = """
holdings:
  - holding_id: hold_US_CRCL_20260701
    symbol: CRCL
    name: Circle Internet Group
    market: US
    shares: 254
    avg_cost: 109.157
    currency: USD
    entry_date: "2026-07-01"
    status: open
    notes: "test fixture"
"""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class _FakeProvider:
    def __init__(self, bars: pd.DataFrame):
        self._bars = bars

    def get_daily_bars(self, symbol, market, start, end):
        return self._bars[(self._bars["trade_date"] >= start) & (self._bars["trade_date"] <= end)]

    def get_index_bars(self, index_code, market, start, end):
        return pd.DataFrame()

    def get_stock_basic(self, market):
        return pd.DataFrame()


def _bars_from(start_compact: str, closes: list[float]) -> pd.DataFrame:
    base = datetime.strptime(start_compact, "%Y%m%d")
    trade_dates = [(base + timedelta(days=i)).strftime("%Y%m%d") for i in range(len(closes))]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": [1000.0] * len(closes)})


def _write_repo_config(root: Path) -> None:
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "holdings.yaml").write_text(HOLDINGS_YAML, encoding="utf-8")


def _seed_action_recommendation(records_dir: Path, *, rec_id: str, symbol: str = "AAA") -> RecommendationRecord:
    rec = RecommendationRecord(
        recommendation_id=rec_id,
        date="2026-07-01",
        session="pre_market",
        symbol=symbol,
        market="US",
        sector="Fintech",
        status="Action",
        action_label="prepare_entry_plan",
        market_snapshot_id="mkt_20260701_US_pre_market",
        candidate_id=f"cand_20260701_US_{symbol}",
        expert_opinions=["opn_1"],
        support_reasons=["TrendAgent support: fixture"],
        oppose_reasons=[],
        risks=[],
        invalidation_conditions=["fixture invalidation"],
        confidence=0.7,
        decision_summary="fixture decision summary",
        lifecycle_status="open",
        created_at=_now(),
        updated_at=_now(),
    )
    append_jsonl(records_dir / "recommendations.jsonl", rec.model_dump())
    decision = DecisionRecord(
        decision_id=f"dec_{rec_id}",
        recommendation_id=rec_id,
        final_status="Action",
        final_action="prepare_entry_plan",
        support_count=3,
        oppose_count=0,
        neutral_count=1,
        veto_count=0,
        risk_veto_triggered=False,
        confidence=0.7,
        decision_reason="fixture",
        invalidation_conditions=["fixture invalidation"],
        created_at=_now(),
    )
    append_jsonl(records_dir / "decisions.jsonl", decision.model_dump())
    return rec


def _seed_open_trade(records_dir: Path, *, rec_id: str, symbol: str = "AAA") -> PaperTrade:
    trade = PaperTrade(
        paper_trade_id=f"ptr_{rec_id}",
        recommendation_id=rec_id,
        symbol=symbol,
        market="US",
        direction="long",
        entry_date="2026-07-01",
        entry_price=100.0,
        virtual_position_size=1.0,
        status="open",
        created_at=_now(),
        updated_at=_now(),
    )
    append_jsonl(records_dir / "paper_trades.jsonl", trade.model_dump())
    return trade


def test_run_close_succeeds_with_empty_records(tmp_path: Path):
    _write_repo_config(tmp_path)
    provider = _FakeProvider(pd.DataFrame(columns=["trade_date", "close", "vol"]))

    result = run_close_module.run_close(date="2026-07-06", repo_root=tmp_path, provider=provider)

    assert result.updated_trades == []
    assert result.generated_reviews == []
    assert result.created_memories == []
    # Printing the summary over an empty result must not raise.
    run_close_module._print_summary(result)


def test_run_close_updates_open_trades_with_fake_provider(tmp_path: Path):
    _write_repo_config(tmp_path)
    records_dir = tmp_path / "data" / "records"
    rec = _seed_action_recommendation(records_dir, rec_id="rec_1")
    _seed_open_trade(records_dir, rec_id=rec.recommendation_id)

    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]  # entry + 5 post-entry closes -> 5d due
    provider = _FakeProvider(_bars_from("20260701", closes))

    result = run_close_module.run_close(date="2026-07-06", repo_root=tmp_path, provider=provider)

    assert len(result.updated_trades) == 1
    assert result.updated_trades[0].return_5d is not None
    assert result.dashboard_error is None
    assert result.dashboard_path is not None
    assert result.dashboard_path.exists()


def test_run_close_generates_reviews_and_memories_when_due(tmp_path: Path):
    _write_repo_config(tmp_path)
    records_dir = tmp_path / "data" / "records"
    rec = _seed_action_recommendation(records_dir, rec_id="rec_1")
    _seed_open_trade(records_dir, rec_id=rec.recommendation_id)

    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    provider = _FakeProvider(_bars_from("20260701", closes))

    result = run_close_module.run_close(date="2026-07-06", repo_root=tmp_path, provider=provider)

    assert len(result.generated_reviews) == 1
    assert result.generated_reviews[0].horizon == "5d"
    reviews_path = records_dir / "reviews.jsonl"
    assert reviews_path.exists()


def test_run_close_does_not_crash_with_no_config_at_all(tmp_path: Path):
    provider = _FakeProvider(pd.DataFrame(columns=["trade_date", "close", "vol"]))
    result = run_close_module.run_close(date="2026-07-06", repo_root=tmp_path, provider=provider)
    run_close_module._print_summary(result)  # must not raise


def test_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, monkeypatch, capsys):
    _write_repo_config(tmp_path)
    fake_result = run_close_module.CloseResult(date="2026-07-06")
    monkeypatch.setattr(run_close_module, "run_close", lambda **kwargs: fake_result)

    exit_code = run_close_module.main(["--date", "2026-07-06", "--data-dir", str(tmp_path / "data")])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "token" not in captured.out.lower()
    assert "token" not in captured.err.lower()


def test_dashboard_json_reflects_paper_trade_after_close(tmp_path: Path):
    _write_repo_config(tmp_path)
    records_dir = tmp_path / "data" / "records"
    rec = _seed_action_recommendation(records_dir, rec_id="rec_1")
    _seed_open_trade(records_dir, rec_id=rec.recommendation_id)

    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    provider = _FakeProvider(_bars_from("20260701", closes))

    result = run_close_module.run_close(date="2026-07-06", repo_root=tmp_path, provider=provider)

    payload = json.loads(result.dashboard_path.read_text(encoding="utf-8"))
    assert len(payload["paper_trading"]["open_positions_perf"]) == 1
    assert payload["paper_trading"]["open_positions_perf"][0]["ticker"] == "AAA"

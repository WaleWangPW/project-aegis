"""Phase 6 tests for DashboardBuilder's paper_trading/review_note fields —
PHASE6 doc §5.9/§7.5.

Never touches `dashboard/index.html`; never adds new schema fields beyond
what Dashboard v1 already renders.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aegis.dashboard.builder import DashboardBuilder
from aegis.dashboard.schema import validate_dashboard_payload
from aegis.models.paper_trade import PaperTrade
from aegis.models.review import ReviewRecord
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

REPO_ROOT = Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _setup(tmp_path: Path):
    records_dir = tmp_path / "records"
    holdings_path = tmp_path / "holdings.yaml"
    output_path = tmp_path / "dashboard" / "dashboard_data.json"
    holdings_path.write_text(HOLDINGS_YAML, encoding="utf-8")
    return records_dir, holdings_path, output_path


def test_dashboard_index_html_unchanged():
    repo_html = REPO_ROOT / "dashboard" / "index.html"
    vault_html = REPO_ROOT.parent / "dashboard" / "index.html"
    assert repo_html.read_bytes() == vault_html.read_bytes()


def test_paper_trading_honest_empty_state_when_no_trades(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-06", session="pre_market")

    assert payload["paper_trading"] == {"new_today": [], "open_positions_perf": []}
    assert payload["review_note"] == "尚无复盘记录"


def test_dashboard_json_still_validates_with_paper_and_review_data(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    trade = PaperTrade(
        paper_trade_id="ptr_1",
        recommendation_id="rec_1",
        symbol="AAA",
        market="US",
        direction="long",
        entry_date="2026-07-06",
        entry_price=100.0,
        virtual_position_size=1.0,
        status="open",
        created_at=_now(),
        updated_at=_now(),
    )
    append_jsonl(records_dir / "paper_trades.jsonl", trade.model_dump())
    review = ReviewRecord(
        review_id="rev_rec_1_5d",
        recommendation_id="rec_1",
        review_date="2026-07-11",
        horizon="5d",
        outcome="success",
        actual_return=0.05,
        max_drawdown=-0.01,
        decision_quality="good_decision",
        expert_contribution={"TrendAgent": "support"},
        lessons=[],
        created_at=_now(),
    )
    append_jsonl(records_dir / "reviews.jsonl", review.model_dump())

    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)
    payload = builder.build(date="2026-07-06", session="pre_market")

    validated = validate_dashboard_payload(payload)  # must not raise
    assert len(validated["paper_trading"]["new_today"]) == 1
    assert len(validated["paper_trading"]["open_positions_perf"]) == 1
    assert "1 条复盘记录" in validated["review_note"]


def test_existing_crcl_holding_remains_in_dashboard_json(tmp_path: Path):
    records_dir, holdings_path, output_path = _setup(tmp_path)
    builder = DashboardBuilder(records_dir=records_dir, holdings_config_path=holdings_path, output_path=output_path)

    payload = builder.build(date="2026-07-06", session="pre_market")

    tickers = {h["ticker"] for h in payload["holdings"]}
    assert "CRCL" in tickers

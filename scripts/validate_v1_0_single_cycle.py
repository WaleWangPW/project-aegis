#!/usr/bin/env python3
"""Validate the V1.0 single-cycle Review/Memory acceptance target.

This script proves the product-level loop:

    Recommendation -> PaperTrade -> Review -> InvestmentMemory

It runs in an isolated acceptance directory under data/processed and never
writes production data/records. The fixture is deterministic and uses a fake
provider, so the script does not need secrets, broker access, webhooks, or
network data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.data.cache import DataCache  # noqa: E402
from aegis.data.gaps import DataGapRegistry  # noqa: E402
from aegis.market.service import MarketDataService  # noqa: E402
from aegis.models.decision import DecisionRecord  # noqa: E402
from aegis.models.expert_opinion import ExpertOpinion  # noqa: E402
from aegis.models.recommendation import RecommendationRecord  # noqa: E402
from aegis.paper.repository import PaperTradeRepository  # noqa: E402
from aegis.paper.service import PaperTradeService  # noqa: E402
from aegis.recommendation.repository import RecommendationRepository  # noqa: E402
from aegis.utils.jsonl import append_jsonl  # noqa: E402
from scripts.run_close import run_close  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v1_0_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V1_0_SINGLE_CYCLE_ACCEPTANCE_PASS.marker"
FAIL_MARKER = "V1_0_SINGLE_CYCLE_ACCEPTANCE_FAIL.marker"
REPORT_JSON = "v1_0_single_cycle_acceptance_latest.json"
REPORT_MD = "v1_0_single_cycle_acceptance_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v1_0_single_cycle_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _bars_from(start_compact: str, closes: list[float]) -> pd.DataFrame:
    base = datetime.strptime(start_compact, "%Y%m%d")
    trade_dates = [(base + timedelta(days=i)).strftime("%Y%m%d") for i in range(len(closes))]
    return pd.DataFrame({"trade_date": trade_dates, "close": closes, "vol": [1000.0] * len(closes)})


class _AcceptanceProvider:
    def __init__(self, bars: pd.DataFrame):
        self._bars = bars

    def get_daily_bars(self, symbol: str, market: str, start: str, end: str) -> pd.DataFrame:
        return self._bars[(self._bars["trade_date"] >= start) & (self._bars["trade_date"] <= end)].copy()

    def get_index_bars(self, index_code: str, market: str, start: str, end: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_stock_basic(self, market: str) -> pd.DataFrame:
        return pd.DataFrame()


@dataclass
class AcceptancePaths:
    run_dir: Path
    records_dir: Path
    reports_dir: Path
    dashboard_path: Path


def _write_holding_config(run_dir: Path) -> None:
    config_dir = run_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "holdings.yaml").write_text(
        "\n".join(
            [
                "holdings:",
                "  - holding_id: hold_US_AAA_20260701",
                "    symbol: AAA",
                "    name: Aegis Acceptance Fixture",
                "    market: US",
                "    shares: 1",
                "    avg_cost: 100.0",
                "    currency: USD",
                '    entry_date: "2026-07-01"',
                "    status: open",
                '    notes: "V1.0 acceptance fixture, not a real holding"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _seed_recommendation(records_dir: Path) -> RecommendationRecord:
    now = _now_iso()
    rec = RecommendationRecord(
        recommendation_id="rec_20260701_pre_market_US_AAA_v1_0_acceptance",
        date="2026-07-01",
        session="pre_market",
        symbol="AAA",
        name="Aegis Acceptance Fixture",
        market="US",
        sector="Acceptance",
        status="Action",
        action_label="prepare_entry_plan",
        market_snapshot_id="mkt_20260701_US_pre_market_v1_0_acceptance",
        candidate_id="cand_20260701_US_AAA_v1_0_acceptance",
        expert_opinions=["opn_v1_0_acceptance_trend", "opn_v1_0_acceptance_risk"],
        support_reasons=["TrendAgent support: acceptance fixture with rising post-entry closes."],
        oppose_reasons=[],
        risks=[],
        invalidation_conditions=["Acceptance fixture invalidates if price closes below 95."],
        confidence=0.72,
        decision_summary="V1.0 acceptance fixture: evidence-supported Action, no risk veto.",
        lifecycle_status="open",
        created_at=now,
        updated_at=now,
    )
    decision = DecisionRecord(
        decision_id="dec_20260701_pre_market_US_AAA_v1_0_acceptance",
        recommendation_id=rec.recommendation_id,
        final_status="Action",
        final_action="prepare_entry_plan",
        support_count=2,
        oppose_count=0,
        neutral_count=0,
        veto_count=0,
        risk_veto_triggered=False,
        confidence=0.72,
        decision_reason="V1.0 acceptance fixture decision.",
        invalidation_conditions=rec.invalidation_conditions,
        created_at=now,
    )
    opinions = [
        ExpertOpinion(
            opinion_id="opn_v1_0_acceptance_trend",
            recommendation_id=rec.recommendation_id,
            expert_name="TrendAgent",
            stance="support",
            confidence=0.7,
            evidence=["Acceptance fixture post-entry trend is rising."],
            risks=[],
            missing_data=[],
            summary="Trend supports the fixture Action.",
            created_at=now,
        ),
        ExpertOpinion(
            opinion_id="opn_v1_0_acceptance_risk",
            recommendation_id=rec.recommendation_id,
            expert_name="RiskAgent",
            stance="neutral",
            confidence=0.6,
            evidence=["No fixture risk veto."],
            risks=[],
            missing_data=[],
            summary="Risk does not veto the fixture Action.",
            created_at=now,
        ),
    ]

    repo = RecommendationRepository(records_dir)
    repo.append_recommendation(rec)
    repo.append_decision(decision)
    for opinion in opinions:
        append_jsonl(records_dir / "expert_opinions.jsonl", opinion.model_dump())
    return rec


def _create_initial_trade(rec: RecommendationRecord, run_dir: Path, records_dir: Path, provider: _AcceptanceProvider):
    cache = DataCache(run_dir / "data" / "cache")
    gaps = DataGapRegistry(records_dir / "data_gaps.jsonl")
    market_data_service = MarketDataService(provider=provider, cache=cache, gaps=gaps)
    paper_repo = PaperTradeRepository(records_dir)
    paper_service = PaperTradeService(repository=paper_repo, market_data_service=market_data_service, gaps=gaps)
    trade = paper_service.create_trade_from_recommendation(rec)
    if trade is None:
        raise RuntimeError("Acceptance fixture failed to create a PaperTrade.")
    return trade


def _file_hashes(records_dir: Path, dashboard_path: Optional[Path]) -> dict[str, Optional[str]]:
    paths = {
        "recommendations": records_dir / "recommendations.jsonl",
        "decisions": records_dir / "decisions.jsonl",
        "expert_opinions": records_dir / "expert_opinions.jsonl",
        "paper_trades": records_dir / "paper_trades.jsonl",
        "reviews": records_dir / "reviews.jsonl",
        "memory": records_dir / "memory.jsonl",
        "dashboard": dashboard_path,
    }
    return {name: _sha256(path) if path is not None else None for name, path in paths.items()}


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    records_dir = run_dir / "data" / "records"
    reports_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=False)

    _write_holding_config(run_dir)
    rec = _seed_recommendation(records_dir)
    provider = _AcceptanceProvider(_bars_from("20260701", [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]))
    trade = _create_initial_trade(rec, run_dir, records_dir, provider)

    close_result = run_close(date="2026-07-06", repo_root=run_dir, provider=provider)
    if close_result.dashboard_error:
        raise RuntimeError(f"Dashboard build failed: {close_result.dashboard_error}")

    reviews = close_result.generated_reviews
    memories = close_result.created_memories
    if not reviews:
        raise RuntimeError("No ReviewRecord was generated.")
    if not memories:
        raise RuntimeError("No InvestmentMemory was generated.")

    review = reviews[0]
    memory = memories[0]
    if review.recommendation_id != rec.recommendation_id:
        raise RuntimeError("ReviewRecord does not link to the seeded RecommendationRecord.")
    if review.paper_trade_id != trade.paper_trade_id:
        raise RuntimeError("ReviewRecord does not link to the PaperTrade.")
    if memory.linked_recommendation_id != rec.recommendation_id:
        raise RuntimeError("InvestmentMemory does not link to the RecommendationRecord.")

    dashboard_path = close_result.dashboard_path
    hashes = _file_hashes(records_dir, dashboard_path)
    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V1.0 Review/Memory single-cycle acceptance",
        "isolated": True,
        "production_records_written": False,
        "run_dir": str(run_dir),
        "records_dir": str(records_dir),
        "dashboard_path": str(dashboard_path) if dashboard_path else None,
        "chain": {
            "recommendation_id": rec.recommendation_id,
            "paper_trade_id": trade.paper_trade_id,
            "review_id": review.review_id,
            "memory_id": memory.memory_id,
            "status": "Recommendation -> PaperTrade -> Review -> InvestmentMemory",
        },
        "counts": {
            "updated_trades": len(close_result.updated_trades),
            "generated_reviews": len(reviews),
            "created_memories": len(memories),
        },
        "review": {
            "horizon": review.horizon,
            "outcome": review.outcome,
            "actual_return": review.actual_return,
            "decision_quality": review.decision_quality,
            "lessons_count": len(review.lessons),
        },
        "safety": {
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_secrets": True,
            "no_production_records_mutation": True,
        },
        "hashes": hashes,
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    fail_marker = reports_dir / FAIL_MARKER
    fail_reason = reports_dir / "V1_0_SINGLE_CYCLE_ACCEPTANCE_FAIL_REASON.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V1.0 Single-Cycle Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- run_dir: `{report['run_dir']}`",
                f"- chain: `{report['chain']['status']}`",
                f"- recommendation_id: `{report['chain']['recommendation_id']}`",
                f"- paper_trade_id: `{report['chain']['paper_trade_id']}`",
                f"- review_id: `{report['chain']['review_id']}`",
                f"- memory_id: `{report['chain']['memory_id']}`",
                f"- actual_return: `{report['review']['actual_return']}`",
                f"- decision_quality: `{report['review']['decision_quality']}`",
                "- safety: no real trade, no broker API, no webhook, no secrets, no production records mutation",
                "",
            ]
        ),
        encoding="utf-8",
    )
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V1.0 Review/Memory single-cycle acceptance",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                f"records_dir={report['records_dir']}",
                "production_records_written=false",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    if fail_marker.exists():
        fail_marker.unlink()
    if fail_reason.exists():
        fail_reason.unlink()


def _write_failure(exc: Exception, reports_dir: Path, command: str) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / FAIL_MARKER).write_text(
        "\n".join(
            [
                f"generated_at={_now_iso()}",
                f"command={command}",
                "exit_code=1",
                "target=V1.0 Review/Memory single-cycle acceptance",
                "failed=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "V1_0_SINGLE_CYCLE_ACCEPTANCE_FAIL_REASON.md").write_text(
        f"# V1.0 Single-Cycle Acceptance Failed\n\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Project Aegis V1.0 single-cycle acceptance.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    reports_dir = Path(args.reports_dir)
    try:
        report = run_acceptance(
            output_root=Path(args.output_root),
            reports_dir=reports_dir,
            run_id=args.run_id,
            command=command,
        )
    except Exception as exc:  # noqa: BLE001 - top-level validator must write a fail marker
        _write_failure(exc, reports_dir, command)
        print(f"[v1_0_acceptance] FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("[v1_0_acceptance] PASS")
    print(f"run_id={report['run_id']}")
    print(f"report={reports_dir / REPORT_JSON}")
    print(f"marker={reports_dir / PASS_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

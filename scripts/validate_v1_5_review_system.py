#!/usr/bin/env python3
"""Validate Project Aegis V1.5 Review System acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.memory.repository import MemoryRepository  # noqa: E402
from aegis.memory.service import MemoryService  # noqa: E402
from aegis.models.decision import DecisionRecord  # noqa: E402
from aegis.models.paper_trade import PaperTrade  # noqa: E402
from aegis.models.recommendation import RecommendationRecord  # noqa: E402
from aegis.models.review import ReviewRecord  # noqa: E402
from aegis.paper.repository import PaperTradeRepository  # noqa: E402
from aegis.recommendation.repository import RecommendationRepository  # noqa: E402
from aegis.review.repository import ReviewRepository  # noqa: E402
from aegis.review.system import build_review_system_report, render_review_system_markdown  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v1_5_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V1_5_REVIEW_SYSTEM_PASS.marker"
FAIL_MARKER = "V1_5_REVIEW_SYSTEM_FAIL.marker"
REPORT_JSON = "v1_5_review_system_acceptance_latest.json"
REPORT_MD = "v1_5_review_system_acceptance_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_id() -> str:
    return "v1_5_review_system_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _rec(
    rec_id: str,
    symbol: str,
    *,
    risks: list[str],
    support: list[str],
    oppose: list[str],
) -> RecommendationRecord:
    now = _now_iso()
    return RecommendationRecord(
        recommendation_id=rec_id,
        date="2026-07-01",
        session="pre_market",
        symbol=symbol,
        name=f"{symbol} Acceptance Fixture",
        market="US",
        sector="Acceptance",
        status="Action",
        action_label="prepare_entry_plan",
        market_snapshot_id=f"mkt_{rec_id}",
        candidate_id=f"cand_{rec_id}",
        expert_opinions=[f"opn_{rec_id}_trend", f"opn_{rec_id}_risk"],
        support_reasons=support,
        oppose_reasons=oppose,
        risks=risks,
        invalidation_conditions=["fixture invalidation"],
        confidence=0.7,
        decision_summary=f"{symbol} V1.5 acceptance fixture.",
        lifecycle_status="open",
        created_at=now,
        updated_at=now,
    )


def _decision(rec: RecommendationRecord) -> DecisionRecord:
    return DecisionRecord(
        decision_id=f"dec_{rec.recommendation_id}",
        recommendation_id=rec.recommendation_id,
        final_status="Action",
        final_action="prepare_entry_plan",
        support_count=len(rec.support_reasons),
        oppose_count=len(rec.oppose_reasons),
        neutral_count=0,
        veto_count=0,
        risk_veto_triggered=False,
        confidence=rec.confidence,
        decision_reason=rec.decision_summary,
        invalidation_conditions=rec.invalidation_conditions,
        created_at=_now_iso(),
    )


def _trade(rec: RecommendationRecord, actual_return: float) -> PaperTrade:
    return PaperTrade(
        paper_trade_id=f"ptr_{rec.recommendation_id}",
        recommendation_id=rec.recommendation_id,
        symbol=rec.symbol,
        market=rec.market,
        direction="long",
        entry_date=rec.date,
        entry_price=100.0,
        virtual_position_size=1.0,
        status="open",
        return_5d=actual_return,
        max_drawdown=min(actual_return, 0.0),
        created_at=_now_iso(),
        updated_at=_now_iso(),
    )


def _review(rec: RecommendationRecord, trade: PaperTrade, actual_return: float) -> ReviewRecord:
    success = actual_return > 0
    quality = "good_decision" if success else "poor_decision"
    lessons = (
        [f"{rec.symbol}: support evidence worked and may be reused."]
        if success
        else [f"{rec.symbol}: risk/oppose reasons need stronger filtering before future Action."]
    )
    return ReviewRecord(
        review_id=f"rev_{rec.recommendation_id}_5d",
        recommendation_id=rec.recommendation_id,
        paper_trade_id=trade.paper_trade_id,
        review_date="2026-07-08",
        horizon="5d",
        outcome="success" if success else "failure",
        actual_return=actual_return,
        max_drawdown=trade.max_drawdown,
        decision_quality=quality,
        success_reason="Fixture support reason was confirmed." if success else None,
        failure_reason=None if success else "Fixture risk/oppose reason was confirmed.",
        expert_contribution={"TrendAgent": "support" if success else "oppose", "RiskAgent": "neutral"},
        lessons=lessons,
        created_at=_now_iso(),
    )


def _seed(records_dir: Path) -> None:
    rec_repo = RecommendationRepository(records_dir)
    paper_repo = PaperTradeRepository(records_dir)
    review_repo = ReviewRepository(records_dir)
    memory_repo = MemoryRepository(records_dir)
    memory_service = MemoryService(repository=memory_repo)

    fixtures = [
        (
            _rec(
                "rec_20260701_pre_market_US_WIN_v1_5",
                "WIN",
                risks=[],
                support=["TrendAgent support: fixture winner"],
                oppose=[],
            ),
            0.08,
        ),
        (
            _rec(
                "rec_20260701_pre_market_US_LOSS_v1_5",
                "LOSS",
                risks=["liquidity_risk", "trend_down"],
                support=[],
                oppose=["RiskAgent oppose: fixture loser risk"],
            ),
            -0.06,
        ),
    ]

    for rec, actual_return in fixtures:
        trade = _trade(rec, actual_return)
        review = _review(rec, trade, actual_return)
        rec_repo.append_recommendation(rec)
        rec_repo.append_decision(_decision(rec))
        paper_repo.append(trade)
        review_repo.append(review)
        memory_service.append_memories(memory_service.create_from_review(review))


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
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    _seed(records_dir)
    weekly = build_review_system_report(records_dir=records_dir, start="2026-07-01", end="2026-07-12", period="weekly")
    monthly = build_review_system_report(records_dir=records_dir, start="2026-07-01", end="2026-07-31", period="monthly")

    weekly_path = run_dir / "review_system_weekly.md"
    monthly_path = run_dir / "review_system_monthly.md"
    weekly_json = run_dir / "review_system_weekly.json"
    monthly_json = run_dir / "review_system_monthly.json"
    weekly_path.write_text(render_review_system_markdown(weekly), encoding="utf-8")
    monthly_path.write_text(render_review_system_markdown(monthly), encoding="utf-8")
    weekly_json.write_text(json.dumps(weekly, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    monthly_json.write_text(json.dumps(monthly, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        "weekly_report": weekly["period"] == "weekly" and weekly["review_count"] == 2,
        "monthly_report": monthly["period"] == "monthly" and monthly["review_count"] == 2,
        "error_attribution": len(weekly["error_attribution"]) >= 1,
        "best_and_failed_cases": bool(weekly["best_cases"]) and bool(weekly["failed_cases"]),
        "memory_reuse": weekly["memory_reuse"]["reference_count"] >= 2,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V1.5 acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V1.5 Review System",
        "isolated": True,
        "production_records_written": False,
        "run_dir": str(run_dir),
        "records_dir": str(records_dir),
        "checks": checks,
        "weekly_report": str(weekly_path),
        "monthly_report": str(monthly_path),
        "weekly_json": str(weekly_json),
        "monthly_json": str(monthly_json),
        "summary": {
            "weekly_review_count": weekly["review_count"],
            "monthly_review_count": monthly["review_count"],
            "error_attribution_count": len(weekly["error_attribution"]),
            "memory_reference_count": weekly["memory_reuse"]["reference_count"],
        },
        "safety": {
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_secrets": True,
            "no_strategy_mutation": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "weekly_report": _sha256(weekly_path),
            "monthly_report": _sha256(monthly_path),
            "weekly_json": _sha256(weekly_json),
            "monthly_json": _sha256(monthly_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V1.5 Review System Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- weekly_report: `{report['weekly_report']}`",
                f"- monthly_report: `{report['monthly_report']}`",
                f"- error_attribution_count: `{report['summary']['error_attribution_count']}`",
                f"- memory_reference_count: `{report['summary']['memory_reference_count']}`",
                "- safety: no real trade, no broker API, no webhook, no secrets, no strategy mutation",
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
                "target=V1.5 Review System",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                "production_records_written=false",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for stale in (reports_dir / FAIL_MARKER, reports_dir / "V1_5_REVIEW_SYSTEM_FAIL_REASON.md"):
        if stale.exists():
            stale.unlink()


def _write_failure(exc: Exception, reports_dir: Path, command: str) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / FAIL_MARKER).write_text(
        "\n".join(
            [
                f"generated_at={_now_iso()}",
                f"command={command}",
                "exit_code=1",
                "target=V1.5 Review System",
                "failed=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "V1_5_REVIEW_SYSTEM_FAIL_REASON.md").write_text(
        f"# V1.5 Review System Failed\n\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Project Aegis V1.5 Review System.")
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
    except Exception as exc:  # noqa: BLE001
        _write_failure(exc, reports_dir, command)
        print(f"[v1_5_review_system] FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("[v1_5_review_system] PASS")
    print(f"run_id={report['run_id']}")
    print(f"report={reports_dir / REPORT_JSON}")
    print(f"marker={reports_dir / PASS_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate V2.13-K Finnhub quote feedback to paper simulation review queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis.paper.finnhub_quote_feedback_review_queue import (  # noqa: E402
    build_finnhub_quote_feedback_review_queue_report,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_k_acceptance"
SOURCE_V2_13_J_REPORT_JSON = REPORTS_DIR / "v2_13_j_finnhub_quote_feedback_intake_latest.json"
SOURCE_V2_13_J_PASS_MARKER = REPORTS_DIR / "V2_13_J_FINNHUB_QUOTE_FEEDBACK_INTAKE_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_K_FINNHUB_QUOTE_FEEDBACK_REVIEW_QUEUE_PASS.marker"
FAIL_MARKER = "V2_13_K_FINNHUB_QUOTE_FEEDBACK_REVIEW_QUEUE_FAIL.marker"
REPORT_JSON = "v2_13_k_finnhub_quote_feedback_review_queue_latest.json"
REPORT_MD = "v2_13_k_finnhub_quote_feedback_review_queue_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fingerprint(path: Path) -> dict:
    return {
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": _sha256(path),
    }


def _fingerprints(paths: dict[str, Path]) -> dict[str, dict]:
    return {name: _fingerprint(path) for name, path in paths.items()}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.13-K Finnhub Quote Feedback Review Queue",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- review_queue_count: `{report['summary']['review_queue_count']}`",
        f"- pending_user_price_date_evidence_count: `{report['summary']['pending_user_price_date_evidence_count']}`",
        f"- social_sentiment_status: `{report['summary']['social_sentiment_status']}`",
        f"- next_stage: `{report['summary']['next_stage']}`",
        "",
        "## Boundary",
        "",
        "- 只把 V2.13-J Finnhub quote simulation follow-up candidates 转成 review queue。",
        "- 每个队列项都等待用户补 entry_price、entry_date、证据引用或截图、显式模拟确认、显式复盘确认。",
        "- 不写 PaperTrade、Recommendation、Review 或 Memory。",
        "- 不联网，不接 Broker API，不用 webhook，不自动下单，不给实盘下单信号。",
        "- Social sentiment 仍为套餐/限流阻塞状态，本阶段不绕过。",
        "",
    ]
    for item in report["review_queue"]:
        lines.extend(
            [
                f"## {item['symbol']}",
                "",
                f"- market: `{item['market']}`",
                f"- feedback_id: `{item['feedback_id']}`",
                f"- queue_status: `{item['queue_status']}`",
                f"- missing_fields: `{', '.join(item['missing_fields'])}`",
                f"- ready_to_create_paper_trade: `{item['ready_to_create_paper_trade']}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_13_k_20260712_acceptance",
    command: str | None = None,
    source_v2_13_j_report_json: Path = SOURCE_V2_13_J_REPORT_JSON,
    source_v2_13_j_pass_marker: Path = SOURCE_V2_13_J_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    source_report = _load_json(source_v2_13_j_report_json)
    report = build_finnhub_quote_feedback_review_queue_report(
        source_report,
        run_id=run_id,
        evidence_ref=str(source_v2_13_j_report_json),
        command=command,
    )
    review_queue_json = run_dir / "finnhub_quote_feedback_review_queue.json"
    pending_items_json = run_dir / "finnhub_quote_pending_review_items.json"
    _write_json(review_queue_json, {"review_queue": report["review_queue"]})
    _write_json(pending_items_json, {"pending_review_items": report["review_queue"]})
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.13-K Finnhub Quote Feedback To Paper Simulation Review Queue",
        "report_status_pass": report["overall_status"] == "PASS",
        "source_marker_exists": source_v2_13_j_pass_marker.exists(),
        "review_queue_json_written": review_queue_json.exists(),
        "pending_items_json_written": pending_items_json.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "reviews_not_written": report["reviews_written"] is False,
        "memory_not_written": report["memory_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["source_v2_13_j_report_json"] = str(source_v2_13_j_report_json)
    report["source_v2_13_j_pass_marker"] = str(source_v2_13_j_pass_marker)
    report["review_queue_json"] = str(review_queue_json)
    report["pending_items_json"] = str(pending_items_json)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_j_report_json": _sha256(source_v2_13_j_report_json),
        "source_v2_13_j_pass_marker": _sha256(source_v2_13_j_pass_marker),
        "review_queue_json": _sha256(review_queue_json),
        "pending_items_json": _sha256(pending_items_json),
    }

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(_render_markdown(report), encoding="utf-8")

    marker_name = PASS_MARKER if report["overall_status"] == "PASS" else FAIL_MARKER
    stale = reports_dir / (FAIL_MARKER if marker_name == PASS_MARKER else PASS_MARKER)
    if stale.exists():
        stale.unlink()
    (reports_dir / marker_name).write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={command or ''}",
                f"exit_code={0 if report['overall_status'] == 'PASS' else 1}",
                "target=V2.13-K Finnhub Quote Feedback To Paper Simulation Review Queue",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"review_queue_json={review_queue_json}",
                f"review_queue_json_sha256={_sha256(review_queue_json)}",
                f"pending_items_json={pending_items_json}",
                f"pending_items_json_sha256={_sha256(pending_items_json)}",
                f"source_v2_13_j_report_json={source_v2_13_j_report_json}",
                f"source_v2_13_j_report_json_sha256={_sha256(source_v2_13_j_report_json)}",
                f"review_queue_count={report['summary']['review_queue_count']}",
                f"pending_user_price_date_evidence_count={report['summary']['pending_user_price_date_evidence_count']}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
                "network_used=false",
                "production_records_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "reviews_written=false",
                "memory_written=false",
                "dashboard_contract_changed=false",
                "review_queue_only=true",
                "requires_user_price_before_paper_trade=true",
                "requires_user_entry_date_before_paper_trade=true",
                "requires_user_evidence_before_paper_trade=true",
                "requires_explicit_review_before_paper_trade=true",
                "requires_explicit_simulation_confirmation=true",
                "no_price_fabrication=true",
                "no_date_fabrication=true",
                "no_live_price=true",
                "no_position_size=true",
                "no_live_order_signal=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--run-id", default="v2_13_k_20260712_acceptance")
    parser.add_argument("--source-v2-13-j-report-json", type=Path, default=SOURCE_V2_13_J_REPORT_JSON)
    parser.add_argument("--source-v2-13-j-pass-marker", type=Path, default=SOURCE_V2_13_J_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_j_report_json=args.source_v2_13_j_report_json,
        source_v2_13_j_pass_marker=args.source_v2_13_j_pass_marker,
    )
    print(
        "V2.13-K Finnhub Quote Feedback To Paper Simulation Review Queue",
        report["overall_status"],
        f"review_queue_count={report['summary']['review_queue_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

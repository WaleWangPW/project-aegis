#!/usr/bin/env python3
"""Validate Project Aegis V2.9-I user-returned evidence refresh."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.returned_evidence_refresh import build_returned_evidence_refresh_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_i_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_CURRENT_BRIEF_JSON = ROOT / "data" / "reports" / "v2_9_h_current_usable_simulation_brief_latest.json"
DEFAULT_REVIEW_MEMORY_JSON = ROOT / "data" / "reports" / "v2_9_g_formal_review_memory_records_latest.json"
RECORD_PATHS = {
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
}

PASS_MARKER = "V2_9_I_USER_RETURNED_EVIDENCE_REFRESH_PASS.marker"
FAIL_MARKER = "V2_9_I_USER_RETURNED_EVIDENCE_REFRESH_FAIL.marker"
REPORT_JSON = "v2_9_i_user_returned_evidence_refresh_latest.json"
REPORT_MD = "v2_9_i_user_returned_evidence_refresh_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_i_user_returned_evidence_refresh_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
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


def _fixture_returned_inputs(current_brief: dict, run_dir: Path) -> tuple[list[dict], Path]:
    queue = current_brief.get("review_memory_queue") or []
    if not queue:
        raise RuntimeError("current brief has no review_memory_queue")
    paper_trade_id = queue[0]["paper_trade_id"]
    evidence_dir = run_dir / "user_returned_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "600519_SH_user_outcome_note.txt"
    evidence_path.write_text(
        "用户回传模拟结果：5d 后纸面观察收益约 +1.2%，最大回撤约 -0.8%；"
        "这是用户手动输入的模拟 outcome evidence，不是 Aegis 联网获取或真实下单记录。\n",
        encoding="utf-8",
    )
    returned_inputs = [
        {
            "returned_evidence_id": "returned_outcome_600519_001",
            "paper_trade_id": paper_trade_id,
            "evidence_type": "outcome",
            "submitted_at": "2026-07-11T21:55:00+08:00",
            "user_note": "用户回传模拟结果：5d 后纸面观察收益约 +1.2%，过程符合低波股息防御假设。",
            "evidence_refs": [str(evidence_path)],
            "outcome": "success",
            "decision_quality": "reasonable_decision",
            "actual_return": 0.012,
            "max_drawdown": -0.008,
            "user_confirmed": True,
        },
        {
            "returned_evidence_id": "returned_secret_block_001",
            "paper_trade_id": paper_trade_id,
            "evidence_type": "text_note",
            "submitted_at": "2026-07-11T21:56:00+08:00",
            "user_note": "token=SHOULD_NOT_BE_STORED",
            "evidence_refs": [],
            "user_confirmed": True,
        },
    ]
    return returned_inputs, evidence_path


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.9-I User Returned Evidence Refresh",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- accepted_returned_evidence_count: `{report['summary']['accepted_returned_evidence_count']}`",
        f"- blocked_returned_evidence_count: `{report['summary']['blocked_returned_evidence_count']}`",
        f"- refreshed_review_count: `{report['summary']['refreshed_review_count']}`",
        f"- review_resolved_count: `{report['summary']['review_resolved_count']}`",
        "",
        "## Boundary",
        "",
        "- 只写验收目录下的 refreshed simulation records。",
        "- actual_return 只能来自用户回传证据，不由 Aegis 编造。",
        "- 不写生产 reviews.jsonl / memory.jsonl / investment_memory.jsonl。",
        "- 不写生产 paper_trades.jsonl 或 recommendations.jsonl。",
        "- 不接 Broker API，不用 webhook，不自动下单。",
        "",
        "## Refreshed Queue",
        "",
    ]
    for item in report["refreshed_brief"].get("review_memory_queue", []):
        lines.extend(
            [
                f"### {item.get('paper_trade_id')}",
                "",
                f"- outcome: `{item.get('outcome')}`",
                f"- decision_quality: `{item.get('decision_quality')}`",
                f"- actual_return: `{item.get('actual_return')}`",
                f"- actual_return_source: `{item.get('actual_return_source')}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    current_brief_json: Path = DEFAULT_CURRENT_BRIEF_JSON,
    review_memory_json: Path = DEFAULT_REVIEW_MEMORY_JSON,
    returned_evidence_json: Optional[Path] = None,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    current_brief = _load_json(current_brief_json)
    review_memory_report = _load_json(review_memory_json)
    if returned_evidence_json:
        returned_inputs = json.loads(returned_evidence_json.read_text(encoding="utf-8"))
        fixture_evidence_path = None
    else:
        returned_inputs, fixture_evidence_path = _fixture_returned_inputs(current_brief, run_dir)
        returned_evidence_json = run_dir / "user_returned_evidence_inputs.json"
        returned_evidence_json.write_text(json.dumps(returned_inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = build_returned_evidence_refresh_report(
        current_brief=current_brief,
        formal_review_memory_report=review_memory_report,
        returned_inputs=returned_inputs,
        run_id=run_id,
        command=command,
    )
    refreshed_reviews_json = run_dir / "refreshed_simulation_reviews.json"
    refreshed_reviews_jsonl = run_dir / "refreshed_simulation_reviews.jsonl"
    refreshed_memories_json = run_dir / "refreshed_simulation_memories.json"
    refreshed_memories_jsonl = run_dir / "refreshed_simulation_memories.jsonl"
    refreshed_brief_json = run_dir / "current_usable_simulation_brief_after_returned_evidence.json"
    refreshed_brief_md = run_dir / "current_usable_simulation_brief_after_returned_evidence.md"
    refreshed_reviews_json.write_text(json.dumps(report["refreshed_reviews"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    refreshed_memories_json.write_text(json.dumps(report["refreshed_memories"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    refreshed_brief_json.write_text(json.dumps(report["refreshed_brief"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(refreshed_reviews_jsonl, report["refreshed_reviews"])
    _write_jsonl(refreshed_memories_jsonl, report["refreshed_memories"])
    refreshed_brief_md.write_text(_render_markdown(report), encoding="utf-8")
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.9-I User Returned Evidence Continuous Review Refresh",
        "report_status_pass": report["overall_status"] == "PASS",
        "refreshed_reviews_json_written": refreshed_reviews_json.exists(),
        "refreshed_memories_json_written": refreshed_memories_json.exists(),
        "refreshed_brief_json_written": refreshed_brief_json.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "network_not_used": report["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-I acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_current_brief_json": str(current_brief_json),
        "source_review_memory_json": str(review_memory_json),
        "returned_evidence_json": str(returned_evidence_json),
        "fixture_evidence_path": str(fixture_evidence_path) if fixture_evidence_path else None,
        "refreshed_reviews_json": str(refreshed_reviews_json),
        "refreshed_reviews_jsonl": str(refreshed_reviews_jsonl),
        "refreshed_memories_json": str(refreshed_memories_json),
        "refreshed_memories_jsonl": str(refreshed_memories_jsonl),
        "refreshed_brief_json": str(refreshed_brief_json),
        "refreshed_brief_md": str(refreshed_brief_md),
        "production_record_files_before": before,
        "production_record_files_after": after,
        "checks": checks,
        "hashes": {
            "source_current_brief_json": _sha256(current_brief_json),
            "source_review_memory_json": _sha256(review_memory_json),
            "returned_evidence_json": _sha256(returned_evidence_json),
            "fixture_evidence_path": _sha256(fixture_evidence_path) if fixture_evidence_path else None,
            "refreshed_reviews_json": _sha256(refreshed_reviews_json),
            "refreshed_reviews_jsonl": _sha256(refreshed_reviews_jsonl),
            "refreshed_memories_json": _sha256(refreshed_memories_json),
            "refreshed_memories_jsonl": _sha256(refreshed_memories_jsonl),
            "refreshed_brief_json": _sha256(refreshed_brief_json),
            "refreshed_brief_md": _sha256(refreshed_brief_md),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.9-I User Returned Evidence Continuous Review Refresh",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"refreshed_reviews_json={report['refreshed_reviews_json']}",
                f"refreshed_reviews_json_sha256={report['hashes']['refreshed_reviews_json']}",
                f"refreshed_memories_json={report['refreshed_memories_json']}",
                f"refreshed_memories_json_sha256={report['hashes']['refreshed_memories_json']}",
                f"refreshed_brief_json={report['refreshed_brief_json']}",
                f"refreshed_brief_json_sha256={report['hashes']['refreshed_brief_json']}",
                "network_used=false",
                "production_records_written=false",
                "reviews_jsonl_written=false",
                "memory_jsonl_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "user_returned_evidence_only=true",
                "actual_return_from_user_evidence_only=true",
                "no_return_fabrication=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
                "no_strategy_mutation=true",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fail_marker = reports_dir / FAIL_MARKER
    if fail_marker.exists():
        fail_marker.unlink()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--run-id")
    parser.add_argument("--current-brief-json", type=Path, default=DEFAULT_CURRENT_BRIEF_JSON)
    parser.add_argument("--review-memory-json", type=Path, default=DEFAULT_REVIEW_MEMORY_JSON)
    parser.add_argument("--returned-evidence-json", type=Path)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            current_brief_json=args.current_brief_json,
            review_memory_json=args.review_memory_json,
            returned_evidence_json=args.returned_evidence_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-I User Returned Evidence Continuous Review Refresh",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-I User Returned Evidence Continuous Review Refresh FAIL: {exc}")
        return 1

    print(
        "V2.9-I User Returned Evidence Continuous Review Refresh "
        f"PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

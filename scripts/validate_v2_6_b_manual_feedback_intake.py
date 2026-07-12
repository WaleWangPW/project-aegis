#!/usr/bin/env python3
"""Validate Project Aegis V2.6-B Manual Feedback Intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.feedback.intake import build_manual_feedback_intake_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_6_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_BRIEF_JSON = ROOT / "data" / "reports" / "v2_6_a_usable_suggestion_brief_latest.json"

PASS_MARKER = "V2_6_B_MANUAL_FEEDBACK_INTAKE_PASS.marker"
FAIL_MARKER = "V2_6_B_MANUAL_FEEDBACK_INTAKE_FAIL.marker"
REPORT_JSON = "v2_6_b_manual_feedback_intake_latest.json"
REPORT_MD = "v2_6_b_manual_feedback_intake_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_6_b_manual_feedback_intake_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fixture_feedbacks(screenshot_path: Path, brief: dict) -> list[dict]:
    candidate_items = [item for item in brief.get("items", []) if item.get("brief_status") == "candidate"]
    blocked_items = [item for item in brief.get("items", []) if item.get("brief_status") == "blocked"]
    if not candidate_items or not blocked_items:
        raise ValueError("V2.6-B fixture requires at least one candidate item and one blocked item")
    first_candidate = candidate_items[0]
    second_candidate = candidate_items[1] if len(candidate_items) > 1 else candidate_items[0]
    blocked_item = blocked_items[0]
    return [
        {
            "feedback_id": "fb_v2_6_b_001",
            "suggestion_id": first_candidate["suggestion_id"],
            "symbol": first_candidate["symbol"],
            "market": first_candidate["market"],
            "feedback_type": "manual_watch",
            "user_note": "已阅读简报，先加入外部软件观察列表，不下单。",
            "screenshot_paths": [str(screenshot_path)],
            "submitted_at": "2026-07-11T19:18:00+08:00",
        },
        {
            "feedback_id": "fb_v2_6_b_002",
            "suggestion_id": second_candidate["suggestion_id"],
            "symbol": second_candidate["symbol"],
            "market": second_candidate["market"],
            "feedback_type": "external_manual_execution",
            "user_note": "用户声明已在外部软件手动做模拟/观察记录，Aegis 只记录证据。",
            "external_execution_summary": f"外部手动记录：观察 {second_candidate['symbol']}，不由 Aegis 下单。",
            "screenshot_paths": [],
            "submitted_at": "2026-07-11T19:18:00+08:00",
        },
        {
            "feedback_id": "fb_v2_6_b_003",
            "suggestion_id": blocked_item["suggestion_id"],
            "symbol": blocked_item["symbol"],
            "market": blocked_item["market"],
            "feedback_type": "external_manual_execution",
            "user_note": "尝试对 blocked path 做外部执行记录，应被阻断。",
            "external_execution_summary": "blocked path should not be executable",
            "screenshot_paths": [],
            "submitted_at": "2026-07-11T19:18:00+08:00",
        },
        {
            "feedback_id": "fb_v2_6_b_004",
            "suggestion_id": first_candidate["suggestion_id"],
            "symbol": first_candidate["symbol"],
            "market": first_candidate["market"],
            "feedback_type": "review_note",
            "user_note": "authorization: bearer secret-like text should be blocked",
            "screenshot_paths": [],
            "submitted_at": "2026-07-11T19:18:00+08:00",
        },
    ]


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.6-B Manual Feedback Intake",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- feedback_count: `{report['summary']['feedback_count']}`",
        f"- accepted_count: `{report['summary']['accepted_count']}`",
        f"- blocked_count: `{report['summary']['blocked_count']}`",
        "",
        "## Boundary",
        "",
        "- 只记录用户回传证据。",
        "- 不做真实交易。",
        "- 不接 Broker API。",
        "- 不使用 webhook。",
        "- 不创建订单。",
        "- 不改 PaperTrade 或 RecommendationRecord。",
        "",
        "## Records",
        "",
    ]
    for item in report["records"]:
        lines.extend(
            [
                f"### {item['feedback_id']} - {item['symbol']}",
                "",
                f"- status: `{item['feedback_status']}`",
                f"- type: `{item['feedback_type']}`",
                f"- blocked_by: `{', '.join(item['blocked_by']) or 'none'}`",
                f"- screenshots: `{len(item['screenshot_evidence'])}`",
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
    brief_json: Path = DEFAULT_BRIEF_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    screenshot = run_dir / "fixture_manual_feedback_screenshot.txt"
    screenshot.write_text("fixture screenshot placeholder: no secrets, no account number\n", encoding="utf-8")
    feedbacks_json = run_dir / "manual_feedback_inputs.json"
    brief = json.loads(brief_json.read_text(encoding="utf-8"))
    feedbacks = _fixture_feedbacks(screenshot, brief)
    feedbacks_json.write_text(json.dumps(feedbacks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = build_manual_feedback_intake_report(
        feedbacks,
        brief=brief,
        run_id=run_id,
        evidence_ref=str(brief_json),
        command=command,
    )
    records_json = run_dir / "manual_feedback_records.json"
    records_json.write_text(json.dumps(report["records"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == "V2.6-B Manual Feedback Intake",
        "report_status_pass": report["overall_status"] == "PASS",
        "production_records_not_written": report["production_records_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.6-B acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_brief_json": str(brief_json),
        "feedback_inputs_json": str(feedbacks_json),
        "manual_feedback_records_json": str(records_json),
        "checks": checks,
        "hashes": {
            "source_brief_json": _sha256(brief_json),
            "feedback_inputs_json": _sha256(feedbacks_json),
            "manual_feedback_records_json": _sha256(records_json),
            "fixture_screenshot": _sha256(screenshot),
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
                "target=V2.6-B Manual Feedback Intake",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"manual_feedback_records_json={report['manual_feedback_records_json']}",
                f"manual_feedback_records_json_sha256={report['hashes']['manual_feedback_records_json']}",
                "network_used=false",
                "production_records_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "user_submitted_evidence_only=true",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
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
    parser.add_argument("--brief-json", type=Path, default=DEFAULT_BRIEF_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            brief_json=args.brief_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.6-B Manual Feedback Intake",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.6-B Manual Feedback Intake FAIL: {exc}")
        return 1

    print(f"V2.6-B Manual Feedback Intake PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

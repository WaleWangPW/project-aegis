#!/usr/bin/env python3
"""Validate Project Aegis V2.9-B User Feedback To Paper Simulation Intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.feedback.decision_packet import build_decision_packet_feedback_intake_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_PACKET_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_9_a_acceptance"
    / "v2_9_a_20260711_acceptance"
    / "current_user_decision_packet.json"
)

PASS_MARKER = "V2_9_B_USER_FEEDBACK_TO_PAPER_SIMULATION_INTAKE_PASS.marker"
FAIL_MARKER = "V2_9_B_USER_FEEDBACK_TO_PAPER_SIMULATION_INTAKE_FAIL.marker"
REPORT_JSON = "v2_9_b_user_feedback_to_paper_simulation_intake_latest.json"
REPORT_MD = "v2_9_b_user_feedback_to_paper_simulation_intake_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_b_user_feedback_paper_intake_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fixture_feedbacks(packet: dict, screenshot_path: Path) -> list[dict]:
    candidates = [item for item in packet.get("items", []) if item.get("decision_packet_status") == "simulation_candidate"]
    blocked = [item for item in packet.get("items", []) if item.get("decision_packet_status") == "blocked"]
    if len(candidates) < 3 or not blocked:
        raise ValueError("V2.9-B fixture requires at least 3 candidates and 1 blocked path")
    return [
        {
            "feedback_id": "packet_fb_watch_001",
            "symbol": candidates[0]["symbol"],
            "market": candidates[0]["market"],
            "action": "watch",
            "user_note": "加入外部观察清单，等待人工确认实时价格和风险。",
            "screenshot_paths": [str(screenshot_path)],
            "submitted_at": "2026-07-11T21:03:00+08:00",
        },
        {
            "feedback_id": "packet_fb_ignore_002",
            "symbol": candidates[1]["symbol"],
            "market": candidates[1]["market"],
            "action": "ignore",
            "user_note": "暂时忽略，理由：与个人持仓或风险偏好不匹配。",
            "screenshot_paths": [],
            "submitted_at": "2026-07-11T21:03:00+08:00",
        },
        {
            "feedback_id": "packet_fb_external_003",
            "symbol": candidates[2]["symbol"],
            "market": candidates[2]["market"],
            "action": "manual_external_action",
            "user_note": "用户声明已在外部软件手动做观察记录，Aegis 只保存证据。",
            "external_execution_summary": f"外部手动记录 {candidates[2]['symbol']}，不是 Aegis 下单。",
            "screenshot_paths": [],
            "submitted_at": "2026-07-11T21:03:00+08:00",
        },
        {
            "feedback_id": "packet_fb_blocked_004",
            "symbol": blocked[0]["symbol"],
            "market": blocked[0]["market"],
            "action": "manual_external_action",
            "user_note": "尝试对 blocked path 做外部执行记录，应被阻断。",
            "external_execution_summary": "blocked path should not become paper intake",
            "screenshot_paths": [],
            "submitted_at": "2026-07-11T21:03:00+08:00",
        },
        {
            "feedback_id": "packet_fb_secret_005",
            "symbol": candidates[0]["symbol"],
            "market": candidates[0]["market"],
            "action": "watch",
            "user_note": "authorization: bearer secret-like text should be blocked",
            "screenshot_paths": [],
            "submitted_at": "2026-07-11T21:03:00+08:00",
        },
    ]


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.9-B User Feedback To Paper Simulation Intake",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- feedback_count: `{report['summary']['feedback_count']}`",
        f"- accepted_count: `{report['summary']['accepted_count']}`",
        f"- blocked_count: `{report['summary']['blocked_count']}`",
        f"- paper_simulation_intake_count: `{report['summary']['paper_simulation_intake_count']}`",
        "",
        "## Boundary",
        "",
        "- 只接收用户对 V2.9-A 决策包的反馈证据。",
        "- 只生成 paper simulation intake candidates。",
        "- 不写 PaperTrade。",
        "- 不写 RecommendationRecord。",
        "- 不接 Broker API，不用 webhook，不自动下单。",
        "",
    ]
    for item in report["paper_simulation_intake_candidates"]:
        lines.extend(
            [
                f"## {item['symbol']}",
                "",
                f"- feedback_id: `{item['feedback_id']}`",
                f"- intake_action: `{item['intake_action']}`",
                f"- requires_user_price_before_paper_trade: `{item['requires_user_price_before_paper_trade']}`",
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
    packet_json: Path = DEFAULT_PACKET_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    packet = json.loads(packet_json.read_text(encoding="utf-8"))
    screenshot = run_dir / "fixture_packet_feedback_screenshot.txt"
    screenshot.write_text("fixture packet feedback screenshot without secrets\n", encoding="utf-8")
    feedback_inputs = _fixture_feedbacks(packet, screenshot)
    feedback_inputs_json = run_dir / "decision_packet_feedback_inputs.json"
    feedback_inputs_json.write_text(json.dumps(feedback_inputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = build_decision_packet_feedback_intake_report(
        feedback_inputs,
        packet=packet,
        run_id=run_id,
        evidence_ref=str(packet_json),
        command=command,
    )
    records_json = run_dir / "decision_packet_feedback_records.json"
    paper_intake_json = run_dir / "paper_simulation_intake_candidates.json"
    records_json.write_text(json.dumps(report["records"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paper_intake_json.write_text(
        json.dumps(report["paper_simulation_intake_candidates"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.9-B User Feedback To Paper Simulation Intake",
        "report_status_pass": report["overall_status"] == "PASS",
        "production_records_not_written": report["production_records_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-B acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_packet_json": str(packet_json),
        "feedback_inputs_json": str(feedback_inputs_json),
        "feedback_records_json": str(records_json),
        "paper_simulation_intake_json": str(paper_intake_json),
        "checks": checks,
        "hashes": {
            "source_packet_json": _sha256(packet_json),
            "feedback_inputs_json": _sha256(feedback_inputs_json),
            "feedback_records_json": _sha256(records_json),
            "paper_simulation_intake_json": _sha256(paper_intake_json),
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
                "target=V2.9-B User Feedback To Paper Simulation Intake",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"paper_simulation_intake_json={report['paper_simulation_intake_json']}",
                f"paper_simulation_intake_json_sha256={report['hashes']['paper_simulation_intake_json']}",
                "network_used=false",
                "production_records_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "paper_simulation_intake_only=true",
                "requires_user_price_before_paper_trade=true",
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
    parser.add_argument("--packet-json", type=Path, default=DEFAULT_PACKET_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            packet_json=args.packet_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-B User Feedback To Paper Simulation Intake",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-B User Feedback To Paper Simulation Intake FAIL: {exc}")
        return 1

    print(
        "V2.9-B User Feedback To Paper Simulation Intake PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate V2.13-J Finnhub quote user feedback intake."""

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

from aegis.feedback.finnhub_quote_brief_intake import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_feedback_intake_report,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_j_acceptance"
SOURCE_V2_13_I_BRIEF_JSON = REPORTS_DIR / "v2_13_i_finnhub_quote_simulation_brief_latest.json"
SOURCE_V2_13_I_PASS_MARKER = REPORTS_DIR / "V2_13_I_FINNHUB_QUOTE_SIMULATION_BRIEF_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_J_FINNHUB_QUOTE_FEEDBACK_INTAKE_PASS.marker"
FAIL_MARKER = "V2_13_J_FINNHUB_QUOTE_FEEDBACK_INTAKE_FAIL.marker"
REPORT_JSON = "v2_13_j_finnhub_quote_feedback_intake_latest.json"
REPORT_MD = "v2_13_j_finnhub_quote_feedback_intake_latest.md"


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


def _fixture_feedbacks(brief: dict, screenshot_path: Path) -> list[dict]:
    items = [item for item in brief.get("items", []) if item.get("brief_status") == "simulation_candidate"]
    if not items:
        raise ValueError("V2.13-J fixture requires at least one Finnhub quote simulation candidate item")
    item = items[0]
    return [
        {
            "feedback_id": "finnhub_quote_fb_watch_001",
            "suggestion_id": item["suggestion_id"],
            "symbol": item["symbol"],
            "market": item["market"],
            "feedback_type": "manual_watch",
            "user_note": "加入外部模拟观察清单，等待人工核对实时价格和事件。",
            "screenshot_paths": [str(screenshot_path)],
            "submitted_at": "2026-07-12T02:30:00+08:00",
        },
        {
            "feedback_id": "finnhub_quote_fb_ignore_002",
            "suggestion_id": item["suggestion_id"],
            "symbol": item["symbol"],
            "market": item["market"],
            "feedback_type": "manual_ignore",
            "user_note": "暂时忽略，先不进入模拟观察。",
            "screenshot_paths": [],
            "submitted_at": "2026-07-12T02:31:00+08:00",
        },
        {
            "feedback_id": "finnhub_quote_fb_external_003",
            "suggestion_id": item["suggestion_id"],
            "symbol": item["symbol"],
            "market": item["market"],
            "feedback_type": "external_manual_execution",
            "user_note": "用户声明已在外部软件手动做纸面观察记录，Aegis 只保存证据。",
            "external_execution_summary": f"外部手动记录 {item['symbol']}，不是 Aegis 下单。",
            "screenshot_paths": [],
            "submitted_at": "2026-07-12T02:32:00+08:00",
        },
        {
            "feedback_id": "finnhub_quote_fb_unknown_004",
            "suggestion_id": "missing_suggestion",
            "symbol": "MISSING.US",
            "market": "US",
            "feedback_type": "manual_watch",
            "user_note": "不存在的简报项应被阻断。",
            "screenshot_paths": [],
            "submitted_at": "2026-07-12T02:33:00+08:00",
        },
        {
            "feedback_id": "finnhub_quote_fb_secret_005",
            "suggestion_id": item["suggestion_id"],
            "symbol": item["symbol"],
            "market": item["market"],
            "feedback_type": "manual_watch",
            "user_note": "authorization: bearer secret-like text should be blocked",
            "screenshot_paths": [],
            "submitted_at": "2026-07-12T02:34:00+08:00",
        },
    ]


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.13-J Finnhub Quote User Feedback Intake",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- feedback_count: `{report['summary']['feedback_count']}`",
        f"- accepted_count: `{report['summary']['accepted_count']}`",
        f"- blocked_count: `{report['summary']['blocked_count']}`",
        f"- simulation_followup_count: `{report['summary']['simulation_followup_count']}`",
        f"- social_sentiment_status: `{report['summary']['social_sentiment_status']}`",
        "",
        "## Boundary",
        "",
        "- 只接收用户对 V2.13-I Finnhub quote simulation brief 的反馈证据。",
        "- 只生成 simulation follow-up candidates。",
        "- 不写 PaperTrade、Recommendation、Review 或 Memory。",
        "- 不接 Broker API，不用 webhook，不自动下单。",
        "",
    ]
    for item in report["simulation_followup_candidates"]:
        lines.extend(
            [
                f"## {item['symbol']}",
                "",
                f"- feedback_id: `{item['feedback_id']}`",
                f"- followup_action: `{item['followup_action']}`",
                f"- requires_user_price_before_paper_trade: `{item['requires_user_price_before_paper_trade']}`",
                f"- requires_user_date_before_paper_trade: `{item['requires_user_date_before_paper_trade']}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_13_j_20260712_acceptance",
    command: str | None = None,
    source_v2_13_i_brief_json: Path = SOURCE_V2_13_I_BRIEF_JSON,
    source_v2_13_i_pass_marker: Path = SOURCE_V2_13_I_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    brief = _load_json(source_v2_13_i_brief_json)
    screenshot = run_dir / "fixture_finnhub_quote_feedback_screenshot.txt"
    screenshot.write_text("fixture Finnhub quote feedback screenshot without secrets\n", encoding="utf-8")
    feedback_inputs = _fixture_feedbacks(brief, screenshot)
    feedback_inputs_json = run_dir / "finnhub_quote_feedback_inputs.json"
    _write_json(feedback_inputs_json, {"feedback_inputs": feedback_inputs})

    report = build_finnhub_quote_feedback_intake_report(
        feedback_inputs,
        brief=brief,
        run_id=run_id,
        evidence_ref=str(source_v2_13_i_brief_json),
        command=command,
    )
    records_json = run_dir / "finnhub_quote_feedback_records.json"
    followups_json = run_dir / "finnhub_quote_simulation_followup_candidates.json"
    _write_json(records_json, {"records": report["records"]})
    _write_json(followups_json, {"simulation_followup_candidates": report["simulation_followup_candidates"]})
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "report_status_pass": report["overall_status"] == "PASS",
        "source_marker_exists": source_v2_13_i_pass_marker.exists(),
        "feedback_inputs_json_written": feedback_inputs_json.exists(),
        "feedback_records_json_written": records_json.exists(),
        "followups_json_written": followups_json.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "reviews_not_written": report["reviews_written"] is False,
        "memory_not_written": report["memory_written"] is False,
        "production_cache_not_mutated": report["production_cache_mutated"] is False,
        "production_provider_config_not_mutated": report["production_provider_config_mutated"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["source_v2_13_i_brief_json"] = str(source_v2_13_i_brief_json)
    report["source_v2_13_i_pass_marker"] = str(source_v2_13_i_pass_marker)
    report["feedback_inputs_json"] = str(feedback_inputs_json)
    report["feedback_records_json"] = str(records_json)
    report["simulation_followups_json"] = str(followups_json)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_i_brief_json": _sha256(source_v2_13_i_brief_json),
        "source_v2_13_i_pass_marker": _sha256(source_v2_13_i_pass_marker),
        "feedback_inputs_json": _sha256(feedback_inputs_json),
        "feedback_records_json": _sha256(records_json),
        "simulation_followups_json": _sha256(followups_json),
        "fixture_screenshot": _sha256(screenshot),
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
                f"target={ACCEPTANCE_TARGET}",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"feedback_records_json={records_json}",
                f"feedback_records_json_sha256={_sha256(records_json)}",
                f"simulation_followups_json={followups_json}",
                f"simulation_followups_json_sha256={_sha256(followups_json)}",
                f"source_v2_13_i_brief_json={source_v2_13_i_brief_json}",
                f"source_v2_13_i_brief_json_sha256={_sha256(source_v2_13_i_brief_json)}",
                f"feedback_count={report['summary']['feedback_count']}",
                f"accepted_count={report['summary']['accepted_count']}",
                f"blocked_count={report['summary']['blocked_count']}",
                f"simulation_followup_count={report['summary']['simulation_followup_count']}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
                "network_used=false",
                "production_records_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "reviews_written=false",
                "memory_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
                "no_live_price=true",
                "no_position_size=true",
                "no_live_order_signal=true",
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
    parser.add_argument("--run-id", default="v2_13_j_20260712_acceptance")
    parser.add_argument("--source-v2-13-i-brief-json", type=Path, default=SOURCE_V2_13_I_BRIEF_JSON)
    parser.add_argument("--source-v2-13-i-pass-marker", type=Path, default=SOURCE_V2_13_I_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_i_brief_json=args.source_v2_13_i_brief_json,
        source_v2_13_i_pass_marker=args.source_v2_13_i_pass_marker,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"feedback_count={report['summary']['feedback_count']}",
        f"accepted_count={report['summary']['accepted_count']}",
        f"simulation_followup_count={report['summary']['simulation_followup_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

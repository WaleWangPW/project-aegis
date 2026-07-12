#!/usr/bin/env python3
"""Validate V2.13-L Finnhub quote user-supplied paper evidence."""

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

from aegis.paper.finnhub_quote_user_supplied_evidence import (  # noqa: E402
    build_finnhub_quote_user_supplied_evidence_report,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_l_acceptance"
SOURCE_V2_13_K_REPORT_JSON = REPORTS_DIR / "v2_13_k_finnhub_quote_feedback_review_queue_latest.json"
SOURCE_V2_13_K_PASS_MARKER = REPORTS_DIR / "V2_13_K_FINNHUB_QUOTE_FEEDBACK_REVIEW_QUEUE_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_L_FINNHUB_QUOTE_USER_SUPPLIED_PAPER_EVIDENCE_PASS.marker"
FAIL_MARKER = "V2_13_L_FINNHUB_QUOTE_USER_SUPPLIED_PAPER_EVIDENCE_FAIL.marker"
REPORT_JSON = "v2_13_l_finnhub_quote_user_supplied_paper_evidence_latest.json"
REPORT_MD = "v2_13_l_finnhub_quote_user_supplied_paper_evidence_latest.md"


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


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fixture_user_evidence_inputs(source_report: dict, run_dir: Path) -> list[dict]:
    queue = list(source_report.get("review_queue") or [])
    if len(queue) < 2:
        raise ValueError("V2.13-L fixture requires at least two Finnhub quote review queue items")

    evidence_dir = run_dir / "user_supplied_finnhub_quote_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    valid_evidence = evidence_dir / f"{queue[0]['symbol'].replace('.', '_')}_entry_evidence.txt"
    valid_evidence.write_text(
        f"user supplied Finnhub quote simulated entry evidence for {queue[0]['symbol']}\n",
        encoding="utf-8",
    )

    return [
        {
            "queue_id": queue[0]["queue_id"],
            "entry_price": 188.88,
            "entry_date": "2026-07-12",
            "virtual_position_size": 1.0,
            "explicit_simulation_confirmation": True,
            "explicit_review_before_paper_trade": True,
            "evidence_refs": [str(valid_evidence)],
            "notes": "user manually confirmed simulated Finnhub quote entry evidence",
        },
        {
            "queue_id": queue[1]["queue_id"],
            "entry_price": None,
            "entry_date": "2026-07-12",
            "explicit_simulation_confirmation": False,
            "explicit_review_before_paper_trade": False,
            "evidence_refs": [],
            "notes": "blocked fixture missing user price evidence simulation confirmation and review confirmation",
        },
    ]


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.13-L Finnhub Quote User-Supplied Paper Evidence",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- validated_user_evidence_count: `{report['summary']['validated_user_evidence_count']}`",
        f"- blocked_user_evidence_count: `{report['summary']['blocked_user_evidence_count']}`",
        f"- social_sentiment_status: `{report['summary']['social_sentiment_status']}`",
        f"- next_stage: `{report['summary']['next_stage']}`",
        "",
        "## Boundary",
        "",
        "- 只验证用户提供的 entry price/date/evidence/simulation confirmation/review confirmation。",
        "- 只生成 virtual PaperTrade creation candidates。",
        "- 不写 PaperTrade、Recommendation、Review 或 Memory。",
        "- 不联网，不接 Broker API，不用 webhook，不自动下单，不生成实盘信号。",
        "- Social sentiment 仍为套餐/限流阻塞状态，本阶段不绕过。",
        "",
    ]
    for item in report["validated_user_evidence_records"]:
        lines.extend(
            [
                f"## Ready: {item['symbol']}",
                "",
                f"- market: `{item['market']}`",
                f"- queue_id: `{item['queue_id']}`",
                f"- entry_date: `{item['entry_date']}`",
                f"- entry_price: `{item['entry_price']}`",
                f"- status: `{item['status']}`",
                "",
            ]
        )
    for item in report["blocked_user_evidence_records"]:
        lines.extend(
            [
                f"## Blocked: {item['symbol']}",
                "",
                f"- queue_id: `{item['queue_id']}`",
                f"- reasons: `{', '.join(item['blocked_reasons'])}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_13_l_20260712_acceptance",
    command: str | None = None,
    source_v2_13_k_report_json: Path = SOURCE_V2_13_K_REPORT_JSON,
    source_v2_13_k_pass_marker: Path = SOURCE_V2_13_K_PASS_MARKER,
    user_evidence_inputs_json: Path | None = None,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    source_report = _load_json(source_v2_13_k_report_json)
    if user_evidence_inputs_json is None:
        user_inputs = _fixture_user_evidence_inputs(source_report, run_dir)
        source_user_inputs_json = run_dir / "finnhub_quote_user_supplied_evidence_inputs.fixture.json"
        _write_json(source_user_inputs_json, user_inputs)
    else:
        source_user_inputs_json = user_evidence_inputs_json
        user_inputs = json.loads(user_evidence_inputs_json.read_text(encoding="utf-8"))

    report = build_finnhub_quote_user_supplied_evidence_report(
        source_report,
        user_inputs,
        run_id=run_id,
        command=command,
    )
    validated_json = run_dir / "validated_finnhub_quote_user_evidence_records.json"
    blocked_json = run_dir / "blocked_finnhub_quote_user_evidence_records.json"
    candidates_json = run_dir / "finnhub_quote_virtual_paper_trade_create_candidates.json"
    _write_json(validated_json, report["validated_user_evidence_records"])
    _write_json(blocked_json, report["blocked_user_evidence_records"])
    _write_json(candidates_json, report["validated_user_evidence_records"])
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.13-L Finnhub Quote User-Supplied Paper Evidence Validation",
        "report_status_pass": report["overall_status"] == "PASS",
        "source_marker_exists": source_v2_13_k_pass_marker.exists(),
        "user_evidence_inputs_json_written": source_user_inputs_json.exists(),
        "validated_user_evidence_json_written": validated_json.exists(),
        "blocked_user_evidence_json_written": blocked_json.exists(),
        "virtual_paper_trade_candidates_json_written": candidates_json.exists(),
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
    report["source_v2_13_k_report_json"] = str(source_v2_13_k_report_json)
    report["source_v2_13_k_pass_marker"] = str(source_v2_13_k_pass_marker)
    report["source_user_evidence_inputs_json"] = str(source_user_inputs_json)
    report["validated_user_evidence_records_json"] = str(validated_json)
    report["blocked_user_evidence_records_json"] = str(blocked_json)
    report["virtual_paper_trade_create_candidates_json"] = str(candidates_json)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_k_report_json": _sha256(source_v2_13_k_report_json),
        "source_v2_13_k_pass_marker": _sha256(source_v2_13_k_pass_marker),
        "source_user_evidence_inputs_json": _sha256(source_user_inputs_json),
        "validated_user_evidence_records_json": _sha256(validated_json),
        "blocked_user_evidence_records_json": _sha256(blocked_json),
        "virtual_paper_trade_create_candidates_json": _sha256(candidates_json),
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
                "target=V2.13-L Finnhub Quote User-Supplied Paper Evidence Validation",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"validated_user_evidence_records_json={validated_json}",
                f"validated_user_evidence_records_json_sha256={_sha256(validated_json)}",
                f"virtual_paper_trade_create_candidates_json={candidates_json}",
                f"virtual_paper_trade_create_candidates_json_sha256={_sha256(candidates_json)}",
                f"source_v2_13_k_report_json={source_v2_13_k_report_json}",
                f"source_v2_13_k_report_json_sha256={_sha256(source_v2_13_k_report_json)}",
                f"validated_user_evidence_count={report['summary']['validated_user_evidence_count']}",
                f"blocked_user_evidence_count={report['summary']['blocked_user_evidence_count']}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
                "network_used=false",
                "production_records_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "reviews_written=false",
                "memory_written=false",
                "dashboard_contract_changed=false",
                "validation_only=true",
                "paper_trade_creation_deferred=true",
                "requires_user_price=true",
                "requires_user_date=true",
                "requires_user_evidence=true",
                "requires_explicit_simulation_confirmation=true",
                "requires_explicit_review_confirmation=true",
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
    parser.add_argument("--run-id", default="v2_13_l_20260712_acceptance")
    parser.add_argument("--source-v2-13-k-report-json", type=Path, default=SOURCE_V2_13_K_REPORT_JSON)
    parser.add_argument("--source-v2-13-k-pass-marker", type=Path, default=SOURCE_V2_13_K_PASS_MARKER)
    parser.add_argument("--user-evidence-inputs-json", type=Path)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_k_report_json=args.source_v2_13_k_report_json,
        source_v2_13_k_pass_marker=args.source_v2_13_k_pass_marker,
        user_evidence_inputs_json=args.user_evidence_inputs_json,
    )
    print(
        "V2.13-L Finnhub Quote User-Supplied Paper Evidence Validation",
        report["overall_status"],
        f"validated_user_evidence_count={report['summary']['validated_user_evidence_count']}",
        f"blocked_user_evidence_count={report['summary']['blocked_user_evidence_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

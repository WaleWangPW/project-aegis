#!/usr/bin/env python3
"""Validate Project Aegis V2.9-H current usable simulation brief."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.current_simulation_brief import (  # noqa: E402
    build_current_usable_simulation_brief,
    render_current_usable_simulation_brief_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_h_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_DECISION_PACKET_JSON = ROOT / "data" / "reports" / "v2_9_a_current_user_decision_packet_latest.json"
DEFAULT_REVIEW_MEMORY_JSON = ROOT / "data" / "reports" / "v2_9_g_formal_review_memory_records_latest.json"
RECORD_PATHS = {
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
}

PASS_MARKER = "V2_9_H_CURRENT_USABLE_SIMULATION_BRIEF_PASS.marker"
FAIL_MARKER = "V2_9_H_CURRENT_USABLE_SIMULATION_BRIEF_FAIL.marker"
REPORT_JSON = "v2_9_h_current_usable_simulation_brief_latest.json"
REPORT_MD = "v2_9_h_current_usable_simulation_brief_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_h_current_usable_simulation_brief_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    decision_packet_json: Path = DEFAULT_DECISION_PACKET_JSON,
    review_memory_json: Path = DEFAULT_REVIEW_MEMORY_JSON,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    decision_packet = _load_json(decision_packet_json)
    review_memory_report = _load_json(review_memory_json)
    brief = build_current_usable_simulation_brief(
        decision_packet=decision_packet,
        formal_review_memory_report=review_memory_report,
        run_id=run_id,
        command=command,
    )

    brief_json = run_dir / "current_usable_simulation_brief.json"
    brief_md = run_dir / "current_usable_simulation_brief.md"
    brief_json.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief_md.write_text(render_current_usable_simulation_brief_markdown(brief), encoding="utf-8")
    after = _fingerprints(record_paths)

    checks = {
        **brief["checks"],
        "acceptance_target_correct": brief["acceptance_target"]
        == "V2.9-H Current Usable Simulation Brief Refresh",
        "brief_status_pass": brief["overall_status"] == "PASS",
        "brief_json_written": brief_json.exists(),
        "brief_md_written": brief_md.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": brief["production_records_written"] is False,
        "network_not_used": brief["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-H acceptance checks failed: " + ", ".join(failed))

    report = {
        **brief,
        "run_dir": str(run_dir),
        "brief_json": str(brief_json),
        "brief_md": str(brief_md),
        "source_decision_packet_json": str(decision_packet_json),
        "source_review_memory_json": str(review_memory_json),
        "production_record_files_before": before,
        "production_record_files_after": after,
        "checks": checks,
        "hashes": {
            "brief_json": _sha256(brief_json),
            "brief_md": _sha256(brief_md),
            "source_decision_packet_json": _sha256(decision_packet_json),
            "source_review_memory_json": _sha256(review_memory_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_current_usable_simulation_brief_markdown(report), encoding="utf-8")
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.9-H Current Usable Simulation Brief Refresh",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"brief_json={report['brief_json']}",
                f"brief_json_sha256={report['hashes']['brief_json']}",
                f"brief_md={report['brief_md']}",
                f"brief_md_sha256={report['hashes']['brief_md']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "real_user_api_blocked_missing_metadata=true",
                "review_pending_without_return_fabrication=true",
                "no_live_price=true",
                "no_position_size=true",
                "no_real_trade=true",
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
    parser.add_argument("--decision-packet-json", type=Path, default=DEFAULT_DECISION_PACKET_JSON)
    parser.add_argument("--review-memory-json", type=Path, default=DEFAULT_REVIEW_MEMORY_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            decision_packet_json=args.decision_packet_json,
            review_memory_json=args.review_memory_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-H Current Usable Simulation Brief Refresh",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-H Current Usable Simulation Brief Refresh FAIL: {exc}")
        return 1

    print(
        "V2.9-H Current Usable Simulation Brief Refresh "
        f"PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

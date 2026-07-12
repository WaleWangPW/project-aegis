#!/usr/bin/env python3
"""Validate Project Aegis V2.9-F virtual PaperTrade review/memory bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.review_memory_bridge import build_virtual_trade_review_memory_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_f_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_VIRTUAL_PAPER_TRADES_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_9_e_acceptance"
    / "v2_9_e_20260711_acceptance"
    / "virtual_paper_trades.json"
)
RECORD_PATHS = {
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_9_F_VIRTUAL_PAPER_TRADE_REVIEW_MEMORY_BRIDGE_PASS.marker"
FAIL_MARKER = "V2_9_F_VIRTUAL_PAPER_TRADE_REVIEW_MEMORY_BRIDGE_FAIL.marker"
REPORT_JSON = "v2_9_f_virtual_paper_trade_review_memory_bridge_latest.json"
REPORT_MD = "v2_9_f_virtual_paper_trade_review_memory_bridge_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_f_virtual_review_memory_bridge_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.9-F Virtual PaperTrade Review/Memory Bridge",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- review_link_count: `{report['summary']['review_link_count']}`",
        f"- memory_candidate_count: `{report['summary']['memory_candidate_count']}`",
        "",
        "## Boundary",
        "",
        "- 只生成 review evidence links 和 investment-memory candidates。",
        "- 不写 reviews.jsonl。",
        "- 不写 memory.jsonl / investment_memory.jsonl。",
        "- 不写生产 paper_trades.jsonl。",
        "- 不接 Broker API，不用 webhook，不自动下单。",
        "",
    ]
    for item in report["memory_candidates"]:
        lines.extend(
            [
                f"## {item['symbol']}",
                "",
                f"- paper_trade_id: `{item['paper_trade_id']}`",
                f"- lesson_type: `{item['lesson_type']}`",
                f"- requires_review_before_memory_write: `{item['requires_review_before_memory_write']}`",
                f"- lesson: {item['lesson']}",
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
    virtual_paper_trades_json: Path = DEFAULT_VIRTUAL_PAPER_TRADES_JSON,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    virtual_trades = json.loads(virtual_paper_trades_json.read_text(encoding="utf-8"))
    report = build_virtual_trade_review_memory_report(
        virtual_trades,
        run_id=run_id,
        evidence_ref=str(virtual_paper_trades_json),
        command=command,
    )
    review_links_json = run_dir / "virtual_trade_review_evidence_links.json"
    memory_candidates_json = run_dir / "virtual_trade_memory_candidates.json"
    review_links_json.write_text(json.dumps(report["review_evidence_links"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    memory_candidates_json.write_text(json.dumps(report["memory_candidates"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == "V2.9-F Virtual PaperTrade Review/Memory Bridge",
        "report_status_pass": report["overall_status"] == "PASS",
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "reviews_not_written": report["reviews_written"] is False,
        "memory_records_not_written": report["memory_records_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-F acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_virtual_paper_trades_json": str(virtual_paper_trades_json),
        "review_evidence_links_json": str(review_links_json),
        "memory_candidates_json": str(memory_candidates_json),
        "production_record_files_before": before,
        "production_record_files_after": after,
        "checks": checks,
        "hashes": {
            "source_virtual_paper_trades_json": _sha256(virtual_paper_trades_json),
            "review_evidence_links_json": _sha256(review_links_json),
            "memory_candidates_json": _sha256(memory_candidates_json),
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
                "target=V2.9-F Virtual PaperTrade Review/Memory Bridge",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"review_evidence_links_json={report['review_evidence_links_json']}",
                f"review_evidence_links_json_sha256={report['hashes']['review_evidence_links_json']}",
                f"memory_candidates_json={report['memory_candidates_json']}",
                f"memory_candidates_json_sha256={report['hashes']['memory_candidates_json']}",
                "network_used=false",
                "production_records_written=false",
                "reviews_written=false",
                "memory_records_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "candidate_evidence_only=true",
                "simulation_only=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
                "no_review_record_mutation=true",
                "no_memory_jsonl_mutation=true",
                "no_paper_trade_mutation=true",
                "no_recommendation_mutation=true",
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
    parser.add_argument("--virtual-paper-trades-json", type=Path, default=DEFAULT_VIRTUAL_PAPER_TRADES_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            virtual_paper_trades_json=args.virtual_paper_trades_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-F Virtual PaperTrade Review/Memory Bridge",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-F Virtual PaperTrade Review/Memory Bridge FAIL: {exc}")
        return 1
    print(f"V2.9-F Virtual PaperTrade Review/Memory Bridge PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate Project Aegis V2.9-G formal simulation review/memory records."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.formal_review_memory import build_formal_review_memory_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_g_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_REVIEW_LINKS_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_9_f_acceptance"
    / "v2_9_f_20260711_acceptance"
    / "virtual_trade_review_evidence_links.json"
)
DEFAULT_MEMORY_CANDIDATES_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_9_f_acceptance"
    / "v2_9_f_20260711_acceptance"
    / "virtual_trade_memory_candidates.json"
)
RECORD_PATHS = {
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
}

PASS_MARKER = "V2_9_G_FORMAL_REVIEW_MEMORY_RECORDS_PASS.marker"
FAIL_MARKER = "V2_9_G_FORMAL_REVIEW_MEMORY_RECORDS_FAIL.marker"
REPORT_JSON = "v2_9_g_formal_review_memory_records_latest.json"
REPORT_MD = "v2_9_g_formal_review_memory_records_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_g_formal_review_memory_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.9-G Formal Review/Memory Records",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- formal_review_count: `{report['summary']['formal_review_count']}`",
        f"- formal_memory_count: `{report['summary']['formal_memory_count']}`",
        "",
        "## Boundary",
        "",
        "- 只写验收目录下的 formal simulation records。",
        "- 不写生产 reviews.jsonl / memory.jsonl / investment_memory.jsonl。",
        "- 不写生产 paper_trades.jsonl。",
        "- 不接 Broker API，不用 webhook，不自动下单。",
        "",
    ]
    for item in report["formal_reviews"]:
        lines.extend(
            [
                f"## {item['paper_trade_id']}",
                "",
                f"- review_id: `{item['review_id']}`",
                f"- outcome: `{item['outcome']}`",
                f"- decision_quality: `{item['decision_quality']}`",
                f"- actual_return: `{item['actual_return']}`",
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
    review_links_json: Path = DEFAULT_REVIEW_LINKS_JSON,
    memory_candidates_json: Path = DEFAULT_MEMORY_CANDIDATES_JSON,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    review_links = json.loads(review_links_json.read_text(encoding="utf-8"))
    memory_candidates = json.loads(memory_candidates_json.read_text(encoding="utf-8"))
    report = build_formal_review_memory_report(
        review_links,
        memory_candidates,
        run_id=run_id,
        command=command,
    )
    formal_reviews_json = run_dir / "formal_simulation_reviews.json"
    formal_reviews_jsonl = run_dir / "formal_simulation_reviews.jsonl"
    formal_memories_json = run_dir / "formal_simulation_memories.json"
    formal_memories_jsonl = run_dir / "formal_simulation_memories.jsonl"
    formal_reviews_json.write_text(json.dumps(report["formal_reviews"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    formal_memories_json.write_text(json.dumps(report["formal_memories"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(formal_reviews_jsonl, report["formal_reviews"])
    _write_jsonl(formal_memories_jsonl, report["formal_memories"])
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.9-G Formal Review/Memory Records From Virtual Trade Candidates",
        "report_status_pass": report["overall_status"] == "PASS",
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "reviews_jsonl_not_written": report["reviews_jsonl_written"] is False,
        "memory_jsonl_not_written": report["memory_jsonl_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-G acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_review_links_json": str(review_links_json),
        "source_memory_candidates_json": str(memory_candidates_json),
        "formal_reviews_json": str(formal_reviews_json),
        "formal_reviews_jsonl": str(formal_reviews_jsonl),
        "formal_memories_json": str(formal_memories_json),
        "formal_memories_jsonl": str(formal_memories_jsonl),
        "production_record_files_before": before,
        "production_record_files_after": after,
        "checks": checks,
        "hashes": {
            "source_review_links_json": _sha256(review_links_json),
            "source_memory_candidates_json": _sha256(memory_candidates_json),
            "formal_reviews_json": _sha256(formal_reviews_json),
            "formal_reviews_jsonl": _sha256(formal_reviews_jsonl),
            "formal_memories_json": _sha256(formal_memories_json),
            "formal_memories_jsonl": _sha256(formal_memories_jsonl),
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
                "target=V2.9-G Formal Review/Memory Records From Virtual Trade Candidates",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"formal_reviews_json={report['formal_reviews_json']}",
                f"formal_reviews_json_sha256={report['hashes']['formal_reviews_json']}",
                f"formal_memories_json={report['formal_memories_json']}",
                f"formal_memories_json_sha256={report['hashes']['formal_memories_json']}",
                "network_used=false",
                "production_records_written=false",
                "reviews_jsonl_written=false",
                "memory_jsonl_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
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
    parser.add_argument("--review-links-json", type=Path, default=DEFAULT_REVIEW_LINKS_JSON)
    parser.add_argument("--memory-candidates-json", type=Path, default=DEFAULT_MEMORY_CANDIDATES_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            review_links_json=args.review_links_json,
            memory_candidates_json=args.memory_candidates_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-G Formal Review/Memory Records From Virtual Trade Candidates",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-G Formal Review/Memory Records FAIL: {exc}")
        return 1
    print(f"V2.9-G Formal Review/Memory Records PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

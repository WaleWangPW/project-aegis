#!/usr/bin/env python3
"""Validate V2.13-N Finnhub quote virtual PaperTrade review/memory bridge."""

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

from aegis.paper.finnhub_quote_review_memory_bridge import (  # noqa: E402
    build_finnhub_quote_review_memory_report,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_n_acceptance"
SOURCE_V2_13_M_REPORT_JSON = REPORTS_DIR / "v2_13_m_finnhub_quote_virtual_paper_trade_creation_latest.json"
SOURCE_V2_13_M_PASS_MARKER = REPORTS_DIR / "V2_13_M_FINNHUB_QUOTE_VIRTUAL_PAPER_TRADE_CREATION_PASS.marker"

RECORD_PATHS = {
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_N_FINNHUB_QUOTE_REVIEW_MEMORY_BRIDGE_PASS.marker"
FAIL_MARKER = "V2_13_N_FINNHUB_QUOTE_REVIEW_MEMORY_BRIDGE_FAIL.marker"
REPORT_JSON = "v2_13_n_finnhub_quote_review_memory_bridge_latest.json"
REPORT_MD = "v2_13_n_finnhub_quote_review_memory_bridge_latest.md"


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


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.13-N Finnhub Quote Review/Memory Bridge",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- review_link_count: `{report['summary']['review_link_count']}`",
        f"- memory_candidate_count: `{report['summary']['memory_candidate_count']}`",
        f"- social_sentiment_status: `{report['summary']['social_sentiment_status']}`",
        f"- next_stage: `{report['summary']['next_stage']}`",
        "",
        "## Boundary",
        "",
        "- 只生成 review evidence links 和 investment-memory candidates。",
        "- 不写 reviews.jsonl。",
        "- 不写 memory.jsonl / investment_memory.jsonl。",
        "- 不写生产 paper_trades.jsonl。",
        "- 不接 Broker API，不用 webhook，不自动下单，不生成实盘信号。",
        "- Social sentiment 仍为套餐/限流阻塞状态，本阶段不绕过。",
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
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_13_n_20260712_acceptance",
    command: str | None = None,
    source_v2_13_m_report_json: Path = SOURCE_V2_13_M_REPORT_JSON,
    source_v2_13_m_pass_marker: Path = SOURCE_V2_13_M_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    source_report = _load_json(source_v2_13_m_report_json)
    report = build_finnhub_quote_review_memory_report(
        source_report,
        run_id=run_id,
        evidence_ref=str(source_v2_13_m_report_json),
        command=command,
    )
    review_links_json = run_dir / "finnhub_quote_review_evidence_links.json"
    memory_candidates_json = run_dir / "finnhub_quote_memory_candidates.json"
    _write_json(review_links_json, report["review_evidence_links"])
    _write_json(memory_candidates_json, report["memory_candidates"])
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.13-N Finnhub Quote Virtual PaperTrade Review/Memory Bridge",
        "report_status_pass": report["overall_status"] == "PASS",
        "source_marker_exists": source_v2_13_m_pass_marker.exists(),
        "review_evidence_links_json_written": review_links_json.exists(),
        "memory_candidates_json_written": memory_candidates_json.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "reviews_not_written": report["reviews_written"] is False,
        "memory_records_not_written": report["memory_records_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["source_v2_13_m_report_json"] = str(source_v2_13_m_report_json)
    report["source_v2_13_m_pass_marker"] = str(source_v2_13_m_pass_marker)
    report["review_evidence_links_json"] = str(review_links_json)
    report["memory_candidates_json"] = str(memory_candidates_json)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_m_report_json": _sha256(source_v2_13_m_report_json),
        "source_v2_13_m_pass_marker": _sha256(source_v2_13_m_pass_marker),
        "review_evidence_links_json": _sha256(review_links_json),
        "memory_candidates_json": _sha256(memory_candidates_json),
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
                "target=V2.13-N Finnhub Quote Virtual PaperTrade Review/Memory Bridge",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"review_evidence_links_json={review_links_json}",
                f"review_evidence_links_json_sha256={_sha256(review_links_json)}",
                f"memory_candidates_json={memory_candidates_json}",
                f"memory_candidates_json_sha256={_sha256(memory_candidates_json)}",
                f"source_v2_13_m_report_json={source_v2_13_m_report_json}",
                f"source_v2_13_m_report_json_sha256={_sha256(source_v2_13_m_report_json)}",
                f"review_link_count={report['summary']['review_link_count']}",
                f"memory_candidate_count={report['summary']['memory_candidate_count']}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
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
                "no_webhook=true",
                "no_order_placement=true",
                "no_live_price=true",
                "no_position_size=true",
                "no_live_order_signal=true",
                "no_review_record_mutation=true",
                "no_memory_jsonl_mutation=true",
                "no_paper_trade_mutation=true",
                "no_recommendation_mutation=true",
                "no_strategy_mutation=true",
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
    parser.add_argument("--run-id", default="v2_13_n_20260712_acceptance")
    parser.add_argument("--source-v2-13-m-report-json", type=Path, default=SOURCE_V2_13_M_REPORT_JSON)
    parser.add_argument("--source-v2-13-m-pass-marker", type=Path, default=SOURCE_V2_13_M_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_m_report_json=args.source_v2_13_m_report_json,
        source_v2_13_m_pass_marker=args.source_v2_13_m_pass_marker,
    )
    print(
        "V2.13-N Finnhub Quote Virtual PaperTrade Review/Memory Bridge",
        report["overall_status"],
        f"review_link_count={report['summary']['review_link_count']}",
        f"memory_candidate_count={report['summary']['memory_candidate_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

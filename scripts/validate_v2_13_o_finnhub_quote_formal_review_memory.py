#!/usr/bin/env python3
"""Validate V2.13-O Finnhub quote formal review/memory records."""

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

from aegis.paper.finnhub_quote_formal_review_memory import (  # noqa: E402
    build_finnhub_quote_formal_review_memory_report,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_o_acceptance"
SOURCE_V2_13_N_REPORT_JSON = REPORTS_DIR / "v2_13_n_finnhub_quote_review_memory_bridge_latest.json"
SOURCE_V2_13_N_PASS_MARKER = REPORTS_DIR / "V2_13_N_FINNHUB_QUOTE_REVIEW_MEMORY_BRIDGE_PASS.marker"

RECORD_PATHS = {
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
}

PASS_MARKER = "V2_13_O_FINNHUB_QUOTE_FORMAL_REVIEW_MEMORY_PASS.marker"
FAIL_MARKER = "V2_13_O_FINNHUB_QUOTE_FORMAL_REVIEW_MEMORY_FAIL.marker"
REPORT_JSON = "v2_13_o_finnhub_quote_formal_review_memory_latest.json"
REPORT_MD = "v2_13_o_finnhub_quote_formal_review_memory_latest.md"


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


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.13-O Finnhub Quote Formal Review/Memory",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- formal_review_count: `{report['summary']['formal_review_count']}`",
        f"- formal_memory_count: `{report['summary']['formal_memory_count']}`",
        f"- social_sentiment_status: `{report['summary']['social_sentiment_status']}`",
        f"- next_stage: `{report['summary']['next_stage']}`",
        "",
        "## Boundary",
        "",
        "- 只写验收目录下的 formal simulation ReviewRecord / InvestmentMemory artifacts。",
        "- 不写生产 reviews.jsonl / memory.jsonl / investment_memory.jsonl。",
        "- 不写生产 paper_trades.jsonl / recommendations.jsonl。",
        "- 虚拟交易仍为 open，不编造收益、回撤、退出价或退出日。",
        "- Social sentiment 仍为套餐/限流阻塞状态，本阶段不绕过。",
        "- 不接 Broker API，不用 webhook，不自动下单，不生成实盘信号。",
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
                f"- exit_price: `{item['exit_price']}`",
                f"- outcome_evidence_status: `{item['outcome_evidence_status']}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_13_o_20260712_acceptance",
    command: str | None = None,
    source_v2_13_n_report_json: Path = SOURCE_V2_13_N_REPORT_JSON,
    source_v2_13_n_pass_marker: Path = SOURCE_V2_13_N_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    source_report = _load_json(source_v2_13_n_report_json)
    report = build_finnhub_quote_formal_review_memory_report(
        source_report,
        run_id=run_id,
        command=command,
    )
    formal_reviews_json = run_dir / "finnhub_quote_formal_review_records.json"
    formal_reviews_jsonl = run_dir / "finnhub_quote_formal_review_records.jsonl"
    formal_memories_json = run_dir / "finnhub_quote_formal_investment_memory_records.json"
    formal_memories_jsonl = run_dir / "finnhub_quote_formal_investment_memory_records.jsonl"
    _write_json(formal_reviews_json, report["formal_reviews"])
    _write_jsonl(formal_reviews_jsonl, report["formal_reviews"])
    _write_json(formal_memories_json, report["formal_memories"])
    _write_jsonl(formal_memories_jsonl, report["formal_memories"])
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.13-O Finnhub Quote Formal Review/Memory Records From Virtual Trade Candidates",
        "report_status_pass": report["overall_status"] == "PASS",
        "source_marker_exists": source_v2_13_n_pass_marker.exists(),
        "formal_reviews_json_written": formal_reviews_json.exists(),
        "formal_memories_json_written": formal_memories_json.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "reviews_jsonl_not_written": report["reviews_jsonl_written"] is False,
        "memory_jsonl_not_written": report["memory_jsonl_written"] is False,
        "investment_memory_jsonl_not_written": report["investment_memory_jsonl_written"] is False,
        "paper_trades_not_written": report["paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["source_v2_13_n_report_json"] = str(source_v2_13_n_report_json)
    report["source_v2_13_n_pass_marker"] = str(source_v2_13_n_pass_marker)
    report["formal_reviews_json"] = str(formal_reviews_json)
    report["formal_reviews_jsonl"] = str(formal_reviews_jsonl)
    report["formal_memories_json"] = str(formal_memories_json)
    report["formal_memories_jsonl"] = str(formal_memories_jsonl)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_n_report_json": _sha256(source_v2_13_n_report_json),
        "source_v2_13_n_pass_marker": _sha256(source_v2_13_n_pass_marker),
        "formal_reviews_json": _sha256(formal_reviews_json),
        "formal_reviews_jsonl": _sha256(formal_reviews_jsonl),
        "formal_memories_json": _sha256(formal_memories_json),
        "formal_memories_jsonl": _sha256(formal_memories_jsonl),
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
                "target=V2.13-O Finnhub Quote Formal Review/Memory Records From Virtual Trade Candidates",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"formal_reviews_json={formal_reviews_json}",
                f"formal_reviews_json_sha256={_sha256(formal_reviews_json)}",
                f"formal_memories_json={formal_memories_json}",
                f"formal_memories_json_sha256={_sha256(formal_memories_json)}",
                f"source_v2_13_n_report_json={source_v2_13_n_report_json}",
                f"source_v2_13_n_report_json_sha256={_sha256(source_v2_13_n_report_json)}",
                f"formal_review_count={report['summary']['formal_review_count']}",
                f"formal_memory_count={report['summary']['formal_memory_count']}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
                "network_used=false",
                "production_records_written=false",
                "reviews_jsonl_written=false",
                "memory_jsonl_written=false",
                "investment_memory_jsonl_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "formal_artifacts_only=true",
                "simulation_only=true",
                "no_return_fabrication=true",
                "no_exit_fabrication=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_live_price=true",
                "no_position_size=true",
                "no_live_order_signal=true",
                "no_review_record_production_mutation=true",
                "no_memory_jsonl_production_mutation=true",
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
    parser.add_argument("--run-id", default="v2_13_o_20260712_acceptance")
    parser.add_argument("--source-v2-13-n-report-json", type=Path, default=SOURCE_V2_13_N_REPORT_JSON)
    parser.add_argument("--source-v2-13-n-pass-marker", type=Path, default=SOURCE_V2_13_N_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_n_report_json=args.source_v2_13_n_report_json,
        source_v2_13_n_pass_marker=args.source_v2_13_n_pass_marker,
    )
    print(
        "V2.13-O Finnhub Quote Formal Review/Memory",
        report["overall_status"],
        f"formal_review_count={report['summary']['formal_review_count']}",
        f"formal_memory_count={report['summary']['formal_memory_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate V2.13-P Finnhub quote brief refresh with Review/Memory context."""

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

from aegis.external_sources.finnhub_quote_brief_review_memory_refresh import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_brief_review_memory_refresh,
    render_finnhub_quote_brief_review_memory_refresh_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_p_acceptance"
SOURCE_V2_13_I_REPORT_JSON = REPORTS_DIR / "v2_13_i_finnhub_quote_simulation_brief_latest.json"
SOURCE_V2_13_I_PASS_MARKER = REPORTS_DIR / "V2_13_I_FINNHUB_QUOTE_SIMULATION_BRIEF_PASS.marker"
SOURCE_V2_13_O_REPORT_JSON = REPORTS_DIR / "v2_13_o_finnhub_quote_formal_review_memory_latest.json"
SOURCE_V2_13_O_PASS_MARKER = REPORTS_DIR / "V2_13_O_FINNHUB_QUOTE_FORMAL_REVIEW_MEMORY_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_P_FINNHUB_QUOTE_BRIEF_REVIEW_MEMORY_REFRESH_PASS.marker"
FAIL_MARKER = "V2_13_P_FINNHUB_QUOTE_BRIEF_REVIEW_MEMORY_REFRESH_FAIL.marker"
REPORT_JSON = "v2_13_p_finnhub_quote_brief_review_memory_refresh_latest.json"
REPORT_MD = "v2_13_p_finnhub_quote_brief_review_memory_refresh_latest.md"


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


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_13_p_20260712_acceptance",
    command: str | None = None,
    source_v2_13_i_report_json: Path = SOURCE_V2_13_I_REPORT_JSON,
    source_v2_13_i_pass_marker: Path = SOURCE_V2_13_I_PASS_MARKER,
    source_v2_13_o_report_json: Path = SOURCE_V2_13_O_REPORT_JSON,
    source_v2_13_o_pass_marker: Path = SOURCE_V2_13_O_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    brief_report = _load_json(source_v2_13_i_report_json)
    formal_report = _load_json(source_v2_13_o_report_json)
    report = build_finnhub_quote_brief_review_memory_refresh(
        brief_report,
        formal_report,
        run_id=run_id,
        command=command,
    )
    brief_json = run_dir / "finnhub_quote_current_simulation_brief_with_review_memory.json"
    brief_md = run_dir / "finnhub_quote_current_simulation_brief_with_review_memory.md"
    _write_json(brief_json, report)
    brief_md.write_text(render_finnhub_quote_brief_review_memory_refresh_markdown(report), encoding="utf-8")
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "report_status_pass": report["overall_status"] == "PASS",
        "source_v2_13_i_marker_exists": source_v2_13_i_pass_marker.exists(),
        "source_v2_13_o_marker_exists": source_v2_13_o_pass_marker.exists(),
        "brief_json_written": brief_json.exists(),
        "brief_md_written": brief_md.exists(),
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
    report["brief_json"] = str(brief_json)
    report["brief_md"] = str(brief_md)
    report["source_v2_13_i_report_json"] = str(source_v2_13_i_report_json)
    report["source_v2_13_i_pass_marker"] = str(source_v2_13_i_pass_marker)
    report["source_v2_13_o_report_json"] = str(source_v2_13_o_report_json)
    report["source_v2_13_o_pass_marker"] = str(source_v2_13_o_pass_marker)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_i_report_json": _sha256(source_v2_13_i_report_json),
        "source_v2_13_i_pass_marker": _sha256(source_v2_13_i_pass_marker),
        "source_v2_13_o_report_json": _sha256(source_v2_13_o_report_json),
        "source_v2_13_o_pass_marker": _sha256(source_v2_13_o_pass_marker),
        "brief_json": _sha256(brief_json),
        "brief_md": _sha256(brief_md),
    }
    _write_json(brief_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_finnhub_quote_brief_review_memory_refresh_markdown(report), encoding="utf-8")

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
                f"brief_json={brief_json}",
                f"brief_json_sha256={_sha256(brief_json)}",
                f"brief_md={brief_md}",
                f"brief_md_sha256={_sha256(brief_md)}",
                f"source_v2_13_i_report_json={source_v2_13_i_report_json}",
                f"source_v2_13_i_report_json_sha256={_sha256(source_v2_13_i_report_json)}",
                f"source_v2_13_o_report_json={source_v2_13_o_report_json}",
                f"source_v2_13_o_report_json_sha256={_sha256(source_v2_13_o_report_json)}",
                f"candidate_count={report['summary']['candidate_count']}",
                f"review_memory_context_count={report['summary']['review_memory_context_count']}",
                f"candidate_symbols={','.join(str(x) for x in report['summary']['candidate_symbols'])}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
                f"review_memory_status={report['summary']['review_memory_status']}",
                "network_used=false",
                "production_records_written=false",
                "reviews_jsonl_written=false",
                "memory_jsonl_written=false",
                "investment_memory_jsonl_written=false",
                "paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "formal_review_memory_context_visible=true",
                "simulation_only=true",
                "no_return_fabrication=true",
                "no_exit_fabrication=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
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
    parser.add_argument("--run-id", default="v2_13_p_20260712_acceptance")
    parser.add_argument("--source-v2-13-i-report-json", type=Path, default=SOURCE_V2_13_I_REPORT_JSON)
    parser.add_argument("--source-v2-13-i-pass-marker", type=Path, default=SOURCE_V2_13_I_PASS_MARKER)
    parser.add_argument("--source-v2-13-o-report-json", type=Path, default=SOURCE_V2_13_O_REPORT_JSON)
    parser.add_argument("--source-v2-13-o-pass-marker", type=Path, default=SOURCE_V2_13_O_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_i_report_json=args.source_v2_13_i_report_json,
        source_v2_13_i_pass_marker=args.source_v2_13_i_pass_marker,
        source_v2_13_o_report_json=args.source_v2_13_o_report_json,
        source_v2_13_o_pass_marker=args.source_v2_13_o_pass_marker,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"candidate_count={report['summary']['candidate_count']}",
        f"review_memory_context_count={report['summary']['review_memory_context_count']}",
        f"symbols={','.join(str(x) for x in report['summary']['candidate_symbols'])}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

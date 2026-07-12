#!/usr/bin/env python3
"""Validate V2.12-J H/US virtual PaperTrade creation from validated evidence."""

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

from aegis.paper.h_us_virtual_trade_creation import build_h_us_virtual_trade_creation_report  # noqa: E402

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_12_j_acceptance"
SOURCE_V2_12_I_REPORT_JSON = REPORTS_DIR / "v2_12_i_h_us_user_supplied_paper_evidence_latest.json"
SOURCE_V2_12_I_PASS_MARKER = REPORTS_DIR / "V2_12_I_H_US_USER_SUPPLIED_PAPER_EVIDENCE_PASS.marker"
PRODUCTION_PAPER_TRADES_JSONL = ROOT / "data" / "records" / "paper_trades.jsonl"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": PRODUCTION_PAPER_TRADES_JSONL,
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_12_J_H_US_VIRTUAL_PAPER_TRADE_CREATION_PASS.marker"
FAIL_MARKER = "V2_12_J_H_US_VIRTUAL_PAPER_TRADE_CREATION_FAIL.marker"
REPORT_JSON = "v2_12_j_h_us_virtual_paper_trade_creation_latest.json"
REPORT_MD = "v2_12_j_h_us_virtual_paper_trade_creation_latest.md"


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
        "# V2.12-J H/US Virtual PaperTrade Creation",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- virtual_paper_trade_count: `{report['summary']['virtual_paper_trade_count']}`",
        f"- next_stage: `{report['summary']['next_stage']}`",
        "",
        "## Boundary",
        "",
        "- 只创建验收目录下的 simulation-only virtual PaperTrade ledger。",
        "- 不写生产 `data/records/paper_trades.jsonl`。",
        "- 不写 Recommendation、Review 或 Memory。",
        "- 不联网，不接 Broker API，不用 webhook，不自动下单。",
        "",
    ]
    for item in report["virtual_paper_trades"]:
        lines.extend(
            [
                f"## {item['symbol']}",
                "",
                f"- market: `{item['market']}`",
                f"- paper_trade_id: `{item['paper_trade_id']}`",
                f"- source_queue_id: `{item['source_queue_id']}`",
                f"- entry_date: `{item['entry_date']}`",
                f"- entry_price: `{item['entry_price']}`",
                f"- status: `{item['status']}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_12_j_20260712_acceptance",
    command: str | None = None,
    source_v2_12_i_report_json: Path = SOURCE_V2_12_I_REPORT_JSON,
    source_v2_12_i_pass_marker: Path = SOURCE_V2_12_I_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    source_report = _load_json(source_v2_12_i_report_json)
    report = build_h_us_virtual_trade_creation_report(
        source_report,
        run_id=run_id,
        command=command,
    )
    ledger_json = run_dir / "h_us_virtual_paper_trades.json"
    ledger_jsonl = run_dir / "h_us_virtual_paper_trades.jsonl"
    _write_json(ledger_json, report["virtual_paper_trades"])
    _write_jsonl(ledger_jsonl, report["virtual_paper_trades"])
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.12-J H-US Virtual PaperTrade Creation From Validated Evidence",
        "report_status_pass": report["overall_status"] == "PASS",
        "source_marker_exists": source_v2_12_i_pass_marker.exists(),
        "virtual_paper_trades_json_written": ledger_json.exists(),
        "virtual_paper_trades_jsonl_written": ledger_jsonl.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "production_paper_trades_not_written": report["production_paper_trades_written"] is False,
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
    report["source_v2_12_i_report_json"] = str(source_v2_12_i_report_json)
    report["source_v2_12_i_pass_marker"] = str(source_v2_12_i_pass_marker)
    report["virtual_paper_trades_json"] = str(ledger_json)
    report["virtual_paper_trades_jsonl"] = str(ledger_jsonl)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_12_i_report_json": _sha256(source_v2_12_i_report_json),
        "source_v2_12_i_pass_marker": _sha256(source_v2_12_i_pass_marker),
        "virtual_paper_trades_json": _sha256(ledger_json),
        "virtual_paper_trades_jsonl": _sha256(ledger_jsonl),
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
                "target=V2.12-J H-US Virtual PaperTrade Creation From Validated Evidence",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"virtual_paper_trades_json={ledger_json}",
                f"virtual_paper_trades_json_sha256={_sha256(ledger_json)}",
                f"virtual_paper_trades_jsonl={ledger_jsonl}",
                f"virtual_paper_trades_jsonl_sha256={_sha256(ledger_jsonl)}",
                f"source_v2_12_i_report_json={source_v2_12_i_report_json}",
                f"source_v2_12_i_report_json_sha256={_sha256(source_v2_12_i_report_json)}",
                f"virtual_paper_trade_count={report['summary']['virtual_paper_trade_count']}",
                "network_used=false",
                "production_records_written=false",
                "production_paper_trades_written=false",
                "recommendations_written=false",
                "reviews_written=false",
                "memory_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "run_specific_ledger_only=true",
                "no_price_fabrication=true",
                "no_date_fabrication=true",
                "no_real_trade_execution=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
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
    parser.add_argument("--run-id", default="v2_12_j_20260712_acceptance")
    parser.add_argument("--source-v2-12-i-report-json", type=Path, default=SOURCE_V2_12_I_REPORT_JSON)
    parser.add_argument("--source-v2-12-i-pass-marker", type=Path, default=SOURCE_V2_12_I_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_12_i_report_json=args.source_v2_12_i_report_json,
        source_v2_12_i_pass_marker=args.source_v2_12_i_pass_marker,
    )
    print(
        "V2.12-J H-US Virtual PaperTrade Creation From Validated Evidence",
        report["overall_status"],
        f"virtual_paper_trade_count={report['summary']['virtual_paper_trade_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate Project Aegis V2.9-E virtual PaperTrade creation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.paper.virtual_trade_creation import build_virtual_trade_creation_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_e_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_VALIDATED_EVIDENCE_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_9_d_acceptance"
    / "v2_9_d_20260711_acceptance"
    / "virtual_paper_trade_create_candidates.json"
)
PRODUCTION_PAPER_TRADES_JSONL = ROOT / "data" / "records" / "paper_trades.jsonl"

PASS_MARKER = "V2_9_E_VIRTUAL_PAPER_TRADE_CREATION_PASS.marker"
FAIL_MARKER = "V2_9_E_VIRTUAL_PAPER_TRADE_CREATION_FAIL.marker"
REPORT_JSON = "v2_9_e_virtual_paper_trade_creation_latest.json"
REPORT_MD = "v2_9_e_virtual_paper_trade_creation_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_e_virtual_paper_trade_creation_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.9-E Virtual PaperTrade Creation",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- virtual_paper_trade_count: `{report['summary']['virtual_paper_trade_count']}`",
        "",
        "## Boundary",
        "",
        "- 只创建验收目录下的 simulation-only virtual PaperTrade ledger。",
        "- 不写生产 `data/records/paper_trades.jsonl`。",
        "- 不接 Broker API，不用 webhook，不自动下单。",
        "",
    ]
    for item in report["virtual_paper_trades"]:
        lines.extend(
            [
                f"## {item['symbol']}",
                "",
                f"- market: `{item['market']}`",
                f"- paper_trade_id: `{item['paper_trade_id']}`",
                f"- entry_date: `{item['entry_date']}`",
                f"- entry_price: `{item['entry_price']}`",
                f"- status: `{item['status']}`",
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
    validated_evidence_json: Path = DEFAULT_VALIDATED_EVIDENCE_JSON,
    production_paper_trades_jsonl: Path = PRODUCTION_PAPER_TRADES_JSONL,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprint(production_paper_trades_jsonl)
    validated = json.loads(validated_evidence_json.read_text(encoding="utf-8"))
    report = build_virtual_trade_creation_report(validated, run_id=run_id, command=command)

    ledger_json = run_dir / "virtual_paper_trades.json"
    ledger_jsonl = run_dir / "virtual_paper_trades.jsonl"
    ledger_json.write_text(json.dumps(report["virtual_paper_trades"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(ledger_jsonl, report["virtual_paper_trades"])
    after = _fingerprint(production_paper_trades_jsonl)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.9-E Virtual PaperTrade Creation From Validated Evidence",
        "report_status_pass": report["overall_status"] == "PASS",
        "production_paper_trades_file_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "production_paper_trades_not_written": report["production_paper_trades_written"] is False,
        "recommendations_not_written": report["recommendations_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-E acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_validated_evidence_json": str(validated_evidence_json),
        "virtual_paper_trades_json": str(ledger_json),
        "virtual_paper_trades_jsonl": str(ledger_jsonl),
        "production_paper_trades_jsonl": str(production_paper_trades_jsonl),
        "production_paper_trades_before": before,
        "production_paper_trades_after": after,
        "checks": checks,
        "hashes": {
            "source_validated_evidence_json": _sha256(validated_evidence_json),
            "virtual_paper_trades_json": _sha256(ledger_json),
            "virtual_paper_trades_jsonl": _sha256(ledger_jsonl),
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
                "target=V2.9-E Virtual PaperTrade Creation From Validated Evidence",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"virtual_paper_trades_json={report['virtual_paper_trades_json']}",
                f"virtual_paper_trades_json_sha256={report['hashes']['virtual_paper_trades_json']}",
                f"virtual_paper_trades_jsonl={report['virtual_paper_trades_jsonl']}",
                f"virtual_paper_trades_jsonl_sha256={report['hashes']['virtual_paper_trades_jsonl']}",
                "network_used=false",
                "production_records_written=false",
                "production_paper_trades_written=false",
                "recommendations_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "no_price_fabrication=true",
                "no_date_fabrication=true",
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
    parser.add_argument("--validated-evidence-json", type=Path, default=DEFAULT_VALIDATED_EVIDENCE_JSON)
    parser.add_argument("--production-paper-trades-jsonl", type=Path, default=PRODUCTION_PAPER_TRADES_JSONL)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            validated_evidence_json=args.validated_evidence_json,
            production_paper_trades_jsonl=args.production_paper_trades_jsonl,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-E Virtual PaperTrade Creation From Validated Evidence",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-E Virtual PaperTrade Creation FAIL: {exc}")
        return 1
    print(f"V2.9-E Virtual PaperTrade Creation PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

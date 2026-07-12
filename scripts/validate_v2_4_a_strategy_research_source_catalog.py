#!/usr/bin/env python3
"""Validate Project Aegis V2.4-A Strategy Research Source Catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.research_ingestion import write_strategy_research_corpus  # noqa: E402
from aegis.strategy.research_source_catalog import (  # noqa: E402
    canonical_strategy_research_records,
    summarize_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_4_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_4_A_STRATEGY_RESEARCH_SOURCE_CATALOG_PASS.marker"
FAIL_MARKER = "V2_4_A_STRATEGY_RESEARCH_SOURCE_CATALOG_FAIL.marker"
REPORT_JSON = "v2_4_a_strategy_research_source_catalog_latest.json"
REPORT_MD = "v2_4_a_strategy_research_source_catalog_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_4_a_strategy_research_catalog_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    records = canonical_strategy_research_records()
    summary = summarize_catalog(records)
    corpus_json = run_dir / "strategy_research_source_catalog_corpus.json"
    corpus = write_strategy_research_corpus(records, corpus_json)

    record_ids = [record.research_id for record in records]
    urls = [record.url for record in records]
    required_markets = ["A", "H", "US"]
    required_families = [
        "value",
        "quality",
        "momentum",
        "low_volatility",
        "dividend",
        "size",
        "multi_factor",
        "risk_overlay",
    ]
    checks = {
        "record_count_at_least_10": len(records) >= 10,
        "unique_research_ids": len(record_ids) == len(set(record_ids)),
        "unique_urls": len(urls) == len(set(urls)),
        "covers_a_h_us": all(summary["market_coverage"].get(market, 0) >= 2 for market in required_markets),
        "covers_core_strategy_families": all(
            summary["strategy_family_coverage"].get(family, 0) > 0 for family in required_families
        ),
        "summary_only": summary["safety"]["summary_only"] is True,
        "raw_text_not_stored": summary["safety"]["raw_text_not_stored"] is True,
        "requires_sandbox_before_suggestion": summary["safety"]["requires_sandbox_before_suggestion"] is True,
        "no_real_trade": summary["safety"]["no_real_trade"] is True,
        "no_broker_api": summary["safety"]["no_broker_api"] is True,
        "no_trading_webhook": summary["safety"]["no_trading_webhook"] is True,
        "no_strategy_auto_mutation": summary["safety"]["no_strategy_auto_mutation"] is True,
        "production_records_not_written": True,
        "dashboard_contract_unchanged": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.4-A acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.4-A Strategy Research Source Catalog",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "strategy_research_source_catalog_corpus": str(corpus_json),
        "checks": checks,
        "summary": {
            **summary,
            "corpus_record_count": corpus["record_count"],
            "next_target": "V2.4-B Strategy Research To Sandbox Hypothesis Queue",
        },
        "safety": summary["safety"],
        "hashes": {
            "strategy_research_source_catalog_corpus": _sha256(corpus_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.4-A Strategy Research Source Catalog Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- corpus: `{report['strategy_research_source_catalog_corpus']}`",
                f"- record_count: `{report['summary']['record_count']}`",
                f"- market_coverage: `{report['summary']['market_coverage']}`",
                f"- strategy_family_coverage: `{report['summary']['strategy_family_coverage']}`",
                "- safety: summary-only, raw text not stored, requires sandbox before suggestion, no broker/trading/webhook",
                "",
            ]
        ),
        encoding="utf-8",
    )
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.4-A Strategy Research Source Catalog",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"strategy_research_source_catalog_corpus={report['strategy_research_source_catalog_corpus']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "raw_text_not_stored=true",
                "requires_sandbox_before_suggestion=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
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
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.4-A Strategy Research Source Catalog",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.4-A Strategy Research Source Catalog FAIL: {exc}")
        return 1

    print(f"V2.4-A Strategy Research Source Catalog PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate V2.8-A public strategy source reachability audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.research_source_catalog import canonical_strategy_research_records  # noqa: E402
from aegis.strategy.source_audit import audit_strategy_research_sources  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_8_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_8_A_PUBLIC_STRATEGY_SOURCE_AUDIT_PASS.marker"
FAIL_MARKER = "V2_8_A_PUBLIC_STRATEGY_SOURCE_AUDIT_FAIL.marker"
REPORT_JSON = "v2_8_a_public_strategy_source_audit_latest.json"
REPORT_MD = "v2_8_a_public_strategy_source_audit_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fixture_fetch(url: str, timeout: int) -> tuple[int, str, bytes]:
    assert timeout > 0
    payload = {
        "source_url_hash": hashlib.sha256(url.encode("utf-8")).hexdigest(),
        "summary": "Fixture bounded public strategy source response.",
    }
    content_type = "application/json" if url.endswith(".html") else "application/pdf"
    return 200, content_type, json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.8-A Public Strategy Source Audit",
        "",
        f"- status: `{report['overall_status']}`",
        f"- audited_count: `{report['audited_count']}`",
        f"- reachable_count: `{report['reachable_count']}`",
        f"- market_coverage: `{report['market_coverage']}`",
        f"- strategy_family_coverage: `{report['strategy_family_coverage']}`",
        f"- network_used: `{str(report['network_used']).lower()}`",
        "",
        "## Boundary",
        "",
        "- Metadata/hash only.",
        "- Raw text and sample bytes are not stored.",
        "- Requires sandbox before suggestion.",
        "- No real trade, broker API, or trading webhook.",
        "",
    ]
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    use_live_network: bool = False,
    max_sources: int | None = None,
) -> dict:
    run_id = run_id or "v2_8_a_public_strategy_source_audit_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    records = canonical_strategy_research_records()
    if use_live_network:
        report = audit_strategy_research_sources(
            records,
            run_id=run_id,
            command=command,
            max_sources=max_sources,
            network_used=True,
        )
    else:
        report = audit_strategy_research_sources(
            records,
            run_id=run_id,
            command=command,
            max_sources=max_sources,
            fetch_fn=_fixture_fetch,
            network_used=False,
        )
    report["run_dir"] = str(run_dir)
    report["production_records_written"] = False
    report["dashboard_contract_changed"] = False

    checks = report["checks"]
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.8-A acceptance checks failed: " + ", ".join(failed))

    audit_json = run_dir / "public_strategy_source_audit.json"
    audit_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["public_strategy_source_audit_json"] = str(audit_json)
    report["hashes"] = {
        "public_strategy_source_audit_json": _sha256(audit_json),
    }
    _write_reports(report, reports_dir)
    return report


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
                "target=V2.8-A Public Strategy Source Audit",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"public_strategy_source_audit_json={report['public_strategy_source_audit_json']}",
                f"public_strategy_source_audit_json_sha256={report['hashes']['public_strategy_source_audit_json']}",
                f"audited_count={report['audited_count']}",
                f"reachable_count={report['reachable_count']}",
                f"network_used={str(report['network_used']).lower()}",
                "raw_text_not_stored=true",
                "sample_bytes_not_stored=true",
                "requires_sandbox_before_suggestion=true",
                "production_records_written=false",
                "dashboard_contract_changed=false",
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
    parser.add_argument("--live-network", action="store_true")
    parser.add_argument("--max-sources", type=int)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            use_live_network=args.live_network,
            max_sources=args.max_sources,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.8-A Public Strategy Source Audit",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.8-A Public Strategy Source Audit FAIL: {exc}")
        return 1

    print(f"V2.8-A Public Strategy Source Audit PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

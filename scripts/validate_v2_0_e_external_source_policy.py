#!/usr/bin/env python3
"""Validate Project Aegis V2.0-E External Source Registry and Policy Gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.policy import evaluate_source_registry  # noqa: E402
from aegis.models.external_source import ExternalSourcePolicy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_0_e_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_0_E_EXTERNAL_SOURCE_POLICY_PASS.marker"
FAIL_MARKER = "V2_0_E_EXTERNAL_SOURCE_POLICY_FAIL.marker"
REPORT_JSON = "v2_0_e_external_source_policy_latest.json"
REPORT_MD = "v2_0_e_external_source_policy_latest.md"


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


def _run_id() -> str:
    return "v2_0_e_external_source_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fixture_sources() -> list[ExternalSourcePolicy]:
    return [
        ExternalSourcePolicy(
            source_id="src_bloomberg_unlicensed",
            name="Bloomberg Unlicensed Placeholder",
            source_type="licensed_financial_data",
            access_method="unauthorized_scrape",
            license_status="unknown",
            evidence_level="licensed_provider",
            retention_policy="metadata_only",
            allowed_fields=["source_id", "title", "url_or_external_id", "published_at", "summary", "hash"],
            requires_api_key=True,
            paywalled=True,
            can_collect=False,
            notes="Must be denied until user confirms approved license/API access.",
        ),
        ExternalSourcePolicy(
            source_id="src_sec_company_filings",
            name="SEC Company Filings",
            source_type="regulator",
            access_method="public_page",
            license_status="not_required",
            evidence_level="verified_primary",
            retention_policy="summary_only",
            allowed_fields=["source_id", "title", "url_or_external_id", "published_at", "summary", "hash"],
            requires_api_key=False,
            paywalled=False,
            can_collect=True,
            notes="Official regulator source.",
        ),
        ExternalSourcePolicy(
            source_id="src_reddit_pending",
            name="Reddit API Pending",
            source_type="reddit",
            access_method="official_api",
            license_status="pending",
            evidence_level="community_discussion",
            retention_policy="metadata_only",
            allowed_fields=["source_id", "author_or_publisher", "url_or_external_id", "published_at", "summary", "hash"],
            requires_api_key=True,
            paywalled=False,
            can_collect=True,
            notes="Must be denied until terms/API access are approved.",
        ),
        ExternalSourcePolicy(
            source_id="src_x_pending",
            name="X API Pending",
            source_type="x_twitter",
            access_method="official_api",
            license_status="pending",
            evidence_level="verified_social_statement",
            retention_policy="short_excerpt",
            allowed_fields=["source_id", "author_or_publisher", "url_or_external_id", "published_at", "quoted_excerpt", "hash"],
            requires_api_key=True,
            paywalled=False,
            can_collect=True,
            notes="Must be denied until API access and retention rules are approved.",
        ),
    ]


def _unsafe_scrape_rejected() -> bool:
    try:
        ExternalSourcePolicy(
            source_id="src_bad_scrape",
            name="Bad Scrape",
            source_type="public_web",
            access_method="unauthorized_scrape",
            license_status="unknown",
            evidence_level="unverified_web",
            retention_policy="short_excerpt",
            allowed_fields=[],
            can_collect=True,
        )
    except ValidationError:
        return True
    return False


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

    sources = _fixture_sources()
    registry = evaluate_source_registry(sources)
    registry_json = run_dir / "external_source_policy_gate.json"
    registry_json.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    decisions = {item["source_id"]: item for item in registry["decisions"]}

    checks = {
        "source_registry_present": registry["source_count"] == 4,
        "official_source_allowed": decisions["src_sec_company_filings"]["decision"] == "allow",
        "bloomberg_unlicensed_denied": decisions["src_bloomberg_unlicensed"]["decision"] == "deny",
        "reddit_pending_denied": decisions["src_reddit_pending"]["decision"] == "deny",
        "x_pending_denied": decisions["src_x_pending"]["decision"] == "deny",
        "unsafe_scrape_rejected": _unsafe_scrape_rejected(),
        "no_live_fetch": registry["safety"]["no_live_fetch"] is True,
        "no_secret_or_cookie_access": registry["safety"]["no_cookie_access"] is True and registry["safety"]["no_secret_storage"] is True,
        "no_broker_or_real_trade": registry["safety"]["no_real_trade"] is True and registry["safety"]["no_broker_api"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.0-E acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.0-E External Source Registry and Policy Gate",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "registry_json": str(registry_json),
        "checks": checks,
        "summary": {
            "source_count": registry["source_count"],
            "allow_count": registry["allow_count"],
            "deny_count": registry["deny_count"],
            "allowed_sources": [item["source_id"] for item in registry["decisions"] if item["decision"] == "allow"],
            "denied_sources": [item["source_id"] for item in registry["decisions"] if item["decision"] == "deny"],
        },
        "safety": registry["safety"]
        | {
            "no_live_web_ingestion": True,
            "no_production_records_mutation": True,
            "source_terms_required_before_collection": True,
        },
        "hashes": {
            "registry_json": _sha256(registry_json),
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
                "# V2.0-E External Source Registry and Policy Gate Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- registry_json: `{report['registry_json']}`",
                f"- source_count: `{report['summary']['source_count']}`",
                f"- allow_count: `{report['summary']['allow_count']}`",
                f"- deny_count: `{report['summary']['deny_count']}`",
                "- safety: no live fetch, no cookies, no secrets, no paywall bypass, no real trade",
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
                "target=V2.0-E External Source Registry and Policy Gate",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "network_used=false",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for stale in (reports_dir / FAIL_MARKER, reports_dir / "V2_0_E_EXTERNAL_SOURCE_POLICY_FAIL_REASON.md"):
        if stale.exists():
            stale.unlink()


def _write_failure(exc: Exception, reports_dir: Path, command: str) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / FAIL_MARKER).write_text(
        "\n".join(
            [
                f"generated_at={_now_iso()}",
                f"command={command}",
                "exit_code=1",
                "target=V2.0-E External Source Registry and Policy Gate",
                "failed=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "V2_0_E_EXTERNAL_SOURCE_POLICY_FAIL_REASON.md").write_text(
        f"# V2.0-E External Source Registry and Policy Gate Failed\n\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Project Aegis V2.0-E External Source Policy Gate.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    reports_dir = Path(args.reports_dir)
    try:
        report = run_acceptance(
            output_root=Path(args.output_root),
            reports_dir=reports_dir,
            run_id=args.run_id,
            command=command,
        )
    except Exception as exc:  # noqa: BLE001
        _write_failure(exc, reports_dir, command)
        print(f"[v2_0_e_external_source_policy] FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("[v2_0_e_external_source_policy] PASS")
    print(f"run_id={report['run_id']}")
    print(f"report={reports_dir / REPORT_JSON}")
    print(f"marker={reports_dir / PASS_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

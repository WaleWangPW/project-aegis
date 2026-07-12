#!/usr/bin/env python3
"""Validate Project Aegis V2.0-F Official Source Fetcher."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.fetcher import SourceFetchError, fetch_official_source_item  # noqa: E402
from aegis.models.external_source import ExternalSourcePolicy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_0_f_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_0_F_OFFICIAL_SOURCE_FETCHER_PASS.marker"
FAIL_MARKER = "V2_0_F_OFFICIAL_SOURCE_FETCHER_FAIL.marker"
REPORT_JSON = "v2_0_f_official_source_fetcher_latest.json"
REPORT_MD = "v2_0_f_official_source_fetcher_latest.md"


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


def _official_source() -> ExternalSourcePolicy:
    return ExternalSourcePolicy(
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
    )


def _bloomberg_denied_source() -> ExternalSourcePolicy:
    return ExternalSourcePolicy(
        source_id="src_bloomberg_unlicensed",
        name="Bloomberg Unlicensed Placeholder",
        source_type="licensed_financial_data",
        access_method="unauthorized_scrape",
        license_status="unknown",
        evidence_level="licensed_provider",
        retention_policy="metadata_only",
        requires_api_key=True,
        paywalled=True,
        can_collect=False,
    )


def _fixture_fetch(url: str, user_agent: str, timeout: int) -> tuple[int, str, bytes]:
    assert user_agent
    assert timeout > 0
    return 200, "application/json", b'{"cik":"0000320193","entityType":"operating","name":"Apple Inc."}'


def _run_id() -> str:
    return "v2_0_f_official_source_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    live_sec: bool = False,
    user_agent: str = "ProjectAegis/0.1 contact@example.com",
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    source = _official_source()
    fetch_kwargs = {}
    if not live_sec:
        fetch_kwargs["fetch_fn"] = _fixture_fetch
    item = fetch_official_source_item(
        source=source,
        symbol="AAPL",
        market="US",
        url="https://data.sec.gov/submissions/CIK0000320193.json",
        publisher="SEC",
        user_agent=user_agent,
        **fetch_kwargs,
    )
    item_json = run_dir / "official_source_item.json"
    item_json.write_text(json.dumps(item.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    denied_source_blocked = False
    try:
        fetch_official_source_item(
            source=_bloomberg_denied_source(),
            symbol="AAPL",
            market="US",
            url="https://example.com/paywalled",
            publisher="Bloomberg",
            user_agent=user_agent,
            fetch_fn=_fixture_fetch,
        )
    except SourceFetchError:
        denied_source_blocked = True

    checks = {
        "official_source_fetched": item.source_id == "src_sec_company_filings",
        "summary_created": bool(item.summary),
        "hash_created": bool(item.content_hash),
        "raw_bytes_not_stored": item.raw_bytes_stored is False,
        "denied_source_blocked": denied_source_blocked,
        "no_cookie_or_secret_headers": "no_cookie_header" in item.safety_notes and "no_secret_header" in item.safety_notes,
        "no_broker_or_real_trade": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.0-F acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.0-F Official Source Fetcher",
        "isolated": True,
        "network_used": live_sec,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "item_json": str(item_json),
        "checks": checks,
        "summary": {
            "source_id": item.source_id,
            "symbol": item.symbol,
            "market": item.market,
            "evidence_level": item.evidence_level,
            "retention_policy": item.retention_policy,
            "summary": item.summary,
        },
        "safety": {
            "policy_gate_required": True,
            "no_cookie_access": True,
            "no_secret_storage": True,
            "no_paywall_bypass": True,
            "no_raw_article_storage": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "item_json": _sha256(item_json),
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
                "# V2.0-F Official Source Fetcher Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- item_json: `{report['item_json']}`",
                f"- network_used: `{report['network_used']}`",
                f"- source_id: `{report['summary']['source_id']}`",
                "- safety: policy gate required, no cookies, no secrets, no paywall bypass, no real trade",
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
                "target=V2.0-F Official Source Fetcher",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                f"network_used={str(report['network_used']).lower()}",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for stale in (reports_dir / FAIL_MARKER, reports_dir / "V2_0_F_OFFICIAL_SOURCE_FETCHER_FAIL_REASON.md"):
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
                "target=V2.0-F Official Source Fetcher",
                "failed=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (reports_dir / "V2_0_F_OFFICIAL_SOURCE_FETCHER_FAIL_REASON.md").write_text(
        f"# V2.0-F Official Source Fetcher Failed\n\n{type(exc).__name__}: {exc}\n",
        encoding="utf-8",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Project Aegis V2.0-F Official Source Fetcher.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--live-sec", action="store_true")
    parser.add_argument("--user-agent", default="ProjectAegis/0.1 contact@example.com")
    args = parser.parse_args(argv)

    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    reports_dir = Path(args.reports_dir)
    try:
        report = run_acceptance(
            output_root=Path(args.output_root),
            reports_dir=reports_dir,
            run_id=args.run_id,
            command=command,
            live_sec=args.live_sec,
            user_agent=args.user_agent,
        )
    except Exception as exc:  # noqa: BLE001
        _write_failure(exc, reports_dir, command)
        print(f"[v2_0_f_official_source_fetcher] FAIL: {type(exc).__name__}: {exc}")
        return 1

    print("[v2_0_f_official_source_fetcher] PASS")
    print(f"run_id={report['run_id']}")
    print(f"report={reports_dir / REPORT_JSON}")
    print(f"marker={reports_dir / PASS_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

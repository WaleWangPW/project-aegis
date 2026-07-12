#!/usr/bin/env python3
"""Validate Project Aegis V2.2-C API Research To Sandbox Candidate Bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.validate_v2_2_b_api_backed_research_fetch as fetch_validator  # noqa: E402
from aegis.external_sources.api_fetcher import fetch_external_api_summary  # noqa: E402
from aegis.strategy.library import default_strategy_candidates  # noqa: E402
from aegis.strategy.research_bridge import build_research_bridge_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_2_c_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_2_C_API_RESEARCH_BRIDGE_PASS.marker"
FAIL_MARKER = "V2_2_C_API_RESEARCH_BRIDGE_FAIL.marker"
REPORT_JSON = "v2_2_c_api_research_bridge_latest.json"
REPORT_MD = "v2_2_c_api_research_bridge_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_2_c_api_research_bridge_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fixture_fetch_item():
    return fetch_external_api_summary(
        spec=fetch_validator._approved_research_api(),
        endpoint_path="/strategy-notes",
        query={"market": "A", "family": "low_volatility"},
        env={"AEGIS_RESEARCH_API_KEY": fetch_validator._FIXTURE_SECRET},
        fetch_fn=fetch_validator._fixture_fetch,
    )


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

    fetch_item = _fixture_fetch_item()
    fetch_item_json = run_dir / "api_fetch_item.json"
    fetch_item_json.write_text(json.dumps(fetch_item.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = build_research_bridge_report(
        fetch_items=[fetch_item],
        candidates=default_strategy_candidates(created_at="2026-07-11T00:00:00+08:00"),
        source_fetch_ref=str(fetch_item_json),
        run_id=run_id,
        command=command,
    )
    proposals_json = run_dir / "strategy_update_proposals.json"
    proposals_json.write_text(json.dumps(report["proposals"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report["run_dir"] = str(run_dir)
    report["api_fetch_item_json"] = str(fetch_item_json)
    report["strategy_update_proposals_json"] = str(proposals_json)

    proposals = report["proposals"]
    checks = {
        "bridge_report_passed": report["overall_status"] == "PASS",
        "proposal_created": len(proposals) >= 1,
        "requires_sandbox": all(item["requires_sandbox"] is True for item in proposals),
        "not_auto_applied": all(item["auto_applied"] is False for item in proposals),
        "no_user_facing_suggestion": all(item["user_facing_suggestion_allowed"] is False for item in proposals),
        "fetch_hash_referenced": all(item["proposed_research_refs"] for item in proposals),
        "no_production_records_mutation": report["production_records_written"] is False,
        "no_real_trade_or_broker": report["safety"]["no_real_trade"] is True
        and report["safety"]["no_broker_api"] is True,
        "no_secret_storage": report["safety"]["no_secret_storage"] is True,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.2-C acceptance checks failed: " + ", ".join(failed))

    report["checks"] = checks
    report["hashes"] = {
        "api_fetch_item_json": _sha256(fetch_item_json),
        "strategy_update_proposals_json": _sha256(proposals_json),
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
                "# V2.2-C API Research To Sandbox Candidate Bridge Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- strategy_update_proposals_json: `{report['strategy_update_proposals_json']}`",
                f"- proposal_count: `{report['summary']['proposal_count']}`",
                "- safety: proposal only, requires sandbox, not auto-applied, no user-facing suggestion",
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
                "target=V2.2-C API Research To Sandbox Candidate Bridge",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                f"strategy_update_proposals_json={report['strategy_update_proposals_json']}",
                f"strategy_update_proposals_json_sha256={report['hashes']['strategy_update_proposals_json']}",
                "network_used=false",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "requires_sandbox=true",
                "auto_applied=false",
                "user_facing_suggestion_allowed=false",
                "no_real_trade=true",
                "no_broker_api=true",
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
                    "target=V2.2-C API Research To Sandbox Candidate Bridge",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.2-C API Research To Sandbox Candidate Bridge FAIL: {exc}")
        return 1

    print(f"V2.2-C API Research To Sandbox Candidate Bridge PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

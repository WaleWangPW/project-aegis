#!/usr/bin/env python3
"""Validate V2.8-D historical sandbox rerun from source-audit refresh queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.models.strategy_hypothesis import StrategySandboxHypothesis  # noqa: E402
from aegis.strategy.hypothesis_queue import build_strategy_sandbox_hypotheses  # noqa: E402
from aegis.strategy.hypothesis_sandbox import (  # noqa: E402
    fixture_historical_cases_for_hypotheses,
    strategy_candidates_from_hypotheses,
)
from aegis.strategy.research_source_catalog import canonical_strategy_research_records  # noqa: E402
from aegis.strategy.source_audit_refresh_sandbox import (  # noqa: E402
    build_refresh_queue_historical_sandbox_report,
    refreshed_hypotheses_from_queue,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_8_d_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_REFRESH_QUEUE = (
    ROOT
    / "data"
    / "processed"
    / "v2_8_c_acceptance"
    / "v2_8_c_20260711_acceptance"
    / "source_audit_sandbox_refresh_queue.json"
)
HISTORICAL_CACHE_DIR = ROOT / "data" / "cache" / "p23_2_historical_market"

PASS_MARKER = "V2_8_D_REFRESH_QUEUE_HISTORICAL_SANDBOX_PASS.marker"
FAIL_MARKER = "V2_8_D_REFRESH_QUEUE_HISTORICAL_SANDBOX_FAIL.marker"
REPORT_JSON = "v2_8_d_refresh_queue_historical_sandbox_latest.json"
REPORT_MD = "v2_8_d_refresh_queue_historical_sandbox_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_8_d_refresh_queue_sandbox_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _historical_cache_file_count() -> int:
    if not HISTORICAL_CACHE_DIR.exists():
        return 0
    return sum(1 for _ in HISTORICAL_CACHE_DIR.rglob("*.json"))


def _load_refresh_queue(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hypotheses() -> list[StrategySandboxHypothesis]:
    return build_strategy_sandbox_hypotheses(
        canonical_strategy_research_records(),
        created_at=_now_iso(),
    )


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    refresh_queue_json: Path = DEFAULT_REFRESH_QUEUE,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    refresh_queue = _load_refresh_queue(refresh_queue_json)
    refreshed_hypotheses, proposal_to_hypotheses = refreshed_hypotheses_from_queue(
        refresh_queue,
        _canonical_hypotheses(),
        created_at=_now_iso(),
    )
    candidates = strategy_candidates_from_hypotheses(refreshed_hypotheses)
    cases = fixture_historical_cases_for_hypotheses(refreshed_hypotheses)
    report = build_refresh_queue_historical_sandbox_report(
        refresh_queue,
        refreshed_hypotheses,
        run_id=run_id,
        command=command,
        historical_cache_file_count=_historical_cache_file_count(),
    )

    hypotheses_json = run_dir / "refreshed_hypotheses.json"
    candidates_json = run_dir / "refresh_queue_strategy_candidates.json"
    cases_jsonl = run_dir / "refresh_queue_historical_cases.jsonl"
    sandbox_report_json = run_dir / "refresh_queue_sandbox_report.json"
    hypotheses_json.write_text(
        json.dumps([hypothesis.model_dump() for hypothesis in refreshed_hypotheses], ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    candidates_json.write_text(
        json.dumps([candidate.model_dump() for candidate in candidates], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    cases_jsonl.write_text(
        "".join(json.dumps(case.model_dump(), ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )
    sandbox_report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = report["checks"]
    required_checks = [
        "refresh_queue_passed",
        "all_proposals_evaluated",
        "reachable_refs_used",
        "blocked_refs_excluded",
        "all_hypotheses_require_sandbox",
        "no_direct_user_suggestion",
        "not_auto_applied",
        "historical_cases_present",
        "pass_fail_metrics_present",
        "suggestion_gate_still_required",
        "no_real_trade",
        "no_broker_api",
        "no_trading_webhook",
        "no_strategy_auto_mutation",
        "no_production_records_mutation",
    ]
    failed = [name for name in required_checks if not checks.get(name)]
    if failed:
        raise RuntimeError("V2.8-D acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_refresh_queue_json": str(refresh_queue_json),
        "refreshed_hypotheses_json": str(hypotheses_json),
        "refresh_queue_strategy_candidates_json": str(candidates_json),
        "refresh_queue_historical_cases_jsonl": str(cases_jsonl),
        "refresh_queue_sandbox_report_json": str(sandbox_report_json),
        "proposal_to_hypotheses": proposal_to_hypotheses,
        "dashboard_contract_changed": False,
        "hashes": {
            "source_refresh_queue_json": _sha256(refresh_queue_json),
            "refreshed_hypotheses_json": _sha256(hypotheses_json),
            "refresh_queue_strategy_candidates_json": _sha256(candidates_json),
            "refresh_queue_historical_cases_jsonl": _sha256(cases_jsonl),
            "refresh_queue_sandbox_report_json": _sha256(sandbox_report_json),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


def _render_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# V2.8-D Refresh Queue Historical Sandbox",
            "",
            f"- status: `{report['overall_status']}`",
            f"- run_id: `{report['run_id']}`",
            f"- refresh_queue: `{report['source_refresh_queue_json']}`",
            f"- sandbox_report: `{report['refresh_queue_sandbox_report_json']}`",
            f"- hypothesis_count: `{report['summary']['hypothesis_count']}`",
            f"- historical_case_count: `{report['summary']['historical_case_count']}`",
            f"- pass_count: `{report['summary']['pass_count']}`",
            f"- fail_count: `{report['summary']['fail_count']}`",
            f"- proposal_to_hypotheses: `{report['summary']['proposal_to_hypotheses']}`",
            "",
            "## Boundary",
            "",
            "- Uses V2.8-C refresh queue; no network fetch.",
            "- Blocked source refs are excluded before sandbox evaluation.",
            "- Suggestion Gate is still required before any user-facing brief.",
            "- No real trade, broker API, trading webhook, or production recommendation mutation.",
            "",
        ]
    )


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
                "target=V2.8-D Refresh Queue Historical Sandbox Rerun",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"source_refresh_queue_json={report['source_refresh_queue_json']}",
                f"source_refresh_queue_json_sha256={report['hashes']['source_refresh_queue_json']}",
                f"refresh_queue_sandbox_report_json={report['refresh_queue_sandbox_report_json']}",
                f"refresh_queue_sandbox_report_json_sha256={report['hashes']['refresh_queue_sandbox_report_json']}",
                f"hypothesis_count={report['summary']['hypothesis_count']}",
                f"historical_case_count={report['summary']['historical_case_count']}",
                f"pass_count={report['summary']['pass_count']}",
                f"fail_count={report['summary']['fail_count']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "blocked_source_refs_excluded=true",
                "suggestion_gate_still_required=true",
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
    parser.add_argument("--refresh-queue-json", type=Path, default=DEFAULT_REFRESH_QUEUE)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            refresh_queue_json=args.refresh_queue_json,
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
                    "target=V2.8-D Refresh Queue Historical Sandbox Rerun",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.8-D Refresh Queue Historical Sandbox FAIL: {exc}")
        return 1

    print(
        "V2.8-D Refresh Queue Historical Sandbox PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

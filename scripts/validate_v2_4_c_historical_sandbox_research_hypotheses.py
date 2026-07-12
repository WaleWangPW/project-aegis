#!/usr/bin/env python3
"""Validate Project Aegis V2.4-C Historical Sandbox Run For Research Hypotheses."""

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
from aegis.strategy.hypothesis_sandbox import (  # noqa: E402
    build_hypothesis_sandbox_report,
    fixture_historical_cases_for_hypotheses,
    strategy_candidates_from_hypotheses,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_4_c_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
HISTORICAL_CACHE_DIR = ROOT / "data" / "cache" / "p23_2_historical_market"
HYPOTHESIS_QUEUE_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_4_b_acceptance"
    / "v2_4_b_20260711_acceptance"
    / "strategy_sandbox_hypothesis_queue.json"
)

PASS_MARKER = "V2_4_C_HISTORICAL_SANDBOX_RESEARCH_HYPOTHESES_PASS.marker"
FAIL_MARKER = "V2_4_C_HISTORICAL_SANDBOX_RESEARCH_HYPOTHESES_FAIL.marker"
REPORT_JSON = "v2_4_c_historical_sandbox_research_hypotheses_latest.json"
REPORT_MD = "v2_4_c_historical_sandbox_research_hypotheses_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_4_c_hypothesis_sandbox_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _load_hypotheses(path: Path = HYPOTHESIS_QUEUE_JSON) -> list[StrategySandboxHypothesis]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [StrategySandboxHypothesis(**item) for item in payload["hypotheses"]]


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    hypothesis_queue_json: Path = HYPOTHESIS_QUEUE_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    hypotheses = _load_hypotheses(hypothesis_queue_json)
    candidates = strategy_candidates_from_hypotheses(hypotheses)
    cases = fixture_historical_cases_for_hypotheses(hypotheses)
    candidates_json = run_dir / "hypothesis_strategy_candidates.json"
    cases_jsonl = run_dir / "hypothesis_historical_strategy_cases.jsonl"
    sandbox_report_json = run_dir / "hypothesis_sandbox_report.json"

    candidates_json.write_text(
        json.dumps([candidate.model_dump() for candidate in candidates], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    cases_jsonl.write_text(
        "".join(json.dumps(case.model_dump(), ensure_ascii=False) + "\n" for case in cases),
        encoding="utf-8",
    )

    report = build_hypothesis_sandbox_report(
        hypotheses,
        run_id=run_id,
        command=command,
        historical_cache_file_count=_historical_cache_file_count(),
    )
    sandbox_report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        "sandbox_report_passed": report["overall_status"] == "PASS",
        "all_hypotheses_evaluated": report["summary"]["hypothesis_count"] == len(hypotheses),
        "candidate_count_matches_hypotheses": report["summary"]["candidate_count"] == len(hypotheses),
        "historical_cases_present": report["summary"]["historical_case_count"] == len(hypotheses) * 4,
        "at_least_two_hypotheses_passed": len(report["summary"]["passing_hypotheses"]) >= 2,
        "at_least_two_hypotheses_failed": len(report["summary"]["failing_hypotheses"]) >= 2,
        "metrics_present": all(
            result["metrics"]["win_rate"] is not None
            and result["metrics"]["average_return"] is not None
            and result["metrics"]["max_drawdown"] is not None
            for result in report["results"]
        ),
        "failure_reasons_present": all(
            result["status"] == "PASS" or result["metrics"]["failed_reasons"] for result in report["results"]
        ),
        "historical_cache_detected": report["historical_cache_file_count"] > 0,
        "suggestion_gate_still_required": report["safety"]["suggestion_gate_still_required"] is True,
        "no_real_trade": report["safety"]["no_real_trade"] is True,
        "no_broker_api": report["safety"]["no_broker_api"] is True,
        "no_strategy_auto_mutation": report["safety"]["no_strategy_auto_mutation"] is True,
        "production_records_not_written": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.4-C acceptance checks failed: " + ", ".join(failed))

    acceptance_report = {
        **report,
        "run_dir": str(run_dir),
        "source_hypothesis_queue_json": str(hypothesis_queue_json),
        "hypothesis_strategy_candidates_json": str(candidates_json),
        "hypothesis_historical_cases_jsonl": str(cases_jsonl),
        "hypothesis_sandbox_report_json": str(sandbox_report_json),
        "checks": checks,
        "hashes": {
            "source_hypothesis_queue_json": _sha256(hypothesis_queue_json),
            "hypothesis_strategy_candidates_json": _sha256(candidates_json),
            "hypothesis_historical_cases_jsonl": _sha256(cases_jsonl),
            "hypothesis_sandbox_report_json": _sha256(sandbox_report_json),
        },
    }
    _write_reports(acceptance_report, reports_dir)
    return acceptance_report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.4-C Historical Sandbox Research Hypotheses Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- sandbox_report: `{report['hypothesis_sandbox_report_json']}`",
                f"- hypothesis_count: `{report['summary']['hypothesis_count']}`",
                f"- pass_count: `{report['summary']['pass_count']}`",
                f"- fail_count: `{report['summary']['fail_count']}`",
                f"- passing_hypotheses: `{report['summary']['passing_hypotheses']}`",
                f"- failing_hypotheses: `{report['summary']['failing_hypotheses']}`",
                "- safety: simulation-only, suggestion gate still required, no broker/trading/webhook",
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
                "target=V2.4-C Historical Sandbox Run For Research Hypotheses",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"hypothesis_sandbox_report_json={report['hypothesis_sandbox_report_json']}",
                f"hypothesis_sandbox_report_json_sha256={report['hashes']['hypothesis_sandbox_report_json']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
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
    parser.add_argument("--run-id")
    parser.add_argument("--hypothesis-queue-json", type=Path, default=HYPOTHESIS_QUEUE_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            hypothesis_queue_json=args.hypothesis_queue_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.4-C Historical Sandbox Run For Research Hypotheses",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.4-C Historical Sandbox Research Hypotheses FAIL: {exc}")
        return 1

    print(f"V2.4-C Historical Sandbox Research Hypotheses PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

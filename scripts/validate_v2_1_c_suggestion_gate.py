#!/usr/bin/env python3
"""Validate Project Aegis V2.1-C Suggestion Gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.validate_v2_1_a_historical_strategy_sandbox as sandbox_validator  # noqa: E402
from aegis.models.suggestion import SuggestionOpportunity  # noqa: E402
from aegis.strategy.sandbox import build_strategy_sandbox_report  # noqa: E402
from aegis.strategy.suggestion_gate import build_suggestion_gate_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_1_c_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_1_C_SUGGESTION_GATE_PASS.marker"
FAIL_MARKER = "V2_1_C_SUGGESTION_GATE_FAIL.marker"
REPORT_JSON = "v2_1_c_suggestion_gate_latest.json"
REPORT_MD = "v2_1_c_suggestion_gate_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_1_c_suggestion_gate_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fixture_sandbox_report() -> dict:
    return build_strategy_sandbox_report(
        sandbox_validator._fixture_candidates(),
        sandbox_validator._fixture_cases(),
        run_id="v2_1_c_embedded_sandbox_evidence",
        command="embedded deterministic sandbox evidence",
        historical_cache_file_count=sandbox_validator._historical_cache_file_count(),
    )


def _fixture_opportunities() -> list[SuggestionOpportunity]:
    evidence_refs = [
        "data/reports/v2_1_a_historical_strategy_sandbox_latest.json",
        "data/reports/V2_1_A_HISTORICAL_STRATEGY_SANDBOX_PASS.marker",
    ]
    return [
        SuggestionOpportunity(
            opportunity_id="opp_a_defensive_001",
            strategy_id="low_volatility_dividend_a",
            symbol="600000.SH",
            market="A",
            name="A-share defensive sandbox candidate",
            risk_veto=False,
            evidence_refs=evidence_refs,
            reasons=["Strategy sandbox PASS", "Defensive low-volatility dividend profile"],
            risk_warnings=["Use paper trading only until live recommendation gates pass"],
        ),
        SuggestionOpportunity(
            opportunity_id="opp_us_raw_momentum_001",
            strategy_id="raw_momentum_us",
            symbol="NVDA",
            market="US",
            name="Raw momentum blocked example",
            risk_veto=False,
            evidence_refs=evidence_refs,
            reasons=["Raw momentum candidate requested for gate test"],
            risk_warnings=["Sandbox failed on drawdown and average return"],
        ),
        SuggestionOpportunity(
            opportunity_id="opp_a_risk_veto_001",
            strategy_id="low_volatility_dividend_a",
            symbol="600519.SH",
            market="A",
            name="Risk veto blocked example",
            risk_veto=True,
            evidence_refs=evidence_refs,
            reasons=["Strategy sandbox PASS but risk veto is active"],
            risk_warnings=["Risk veto blocks suggestion"],
        ),
    ]


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

    sandbox_report = _fixture_sandbox_report()
    opportunities = _fixture_opportunities()
    report = build_suggestion_gate_report(opportunities, sandbox_report, run_id=run_id, command=command)

    sandbox_json = run_dir / "embedded_sandbox_report.json"
    opportunities_json = run_dir / "suggestion_opportunities.json"
    suggestions_json = run_dir / "suggestion_drafts.json"
    sandbox_json.write_text(json.dumps(sandbox_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    opportunities_json.write_text(
        json.dumps([item.model_dump() for item in opportunities], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    suggestions_json.write_text(json.dumps(report["suggestions"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report["run_dir"] = str(run_dir)
    report["embedded_sandbox_json"] = str(sandbox_json)
    report["opportunities_json"] = str(opportunities_json)
    report["suggestions_json"] = str(suggestions_json)

    suggestions = report["suggestions"]
    allowed = [item for item in suggestions if item["action"] != "blocked"]
    blocked = [item for item in suggestions if item["action"] == "blocked"]
    checks = {
        "suggestion_gate_passed": report["overall_status"] == "PASS",
        "at_least_one_allowed_draft": len(allowed) >= 1,
        "at_least_one_blocked_draft": len(blocked) >= 1,
        "sandbox_failed_strategy_blocked": any(
            "strategy_sandbox_not_passed" in item["blocked_by"] for item in blocked
        ),
        "risk_veto_blocked": any("risk_veto_triggered" in item["blocked_by"] for item in blocked),
        "evidence_refs_present": all(item["evidence_refs"] for item in suggestions),
        "manual_execution_only": report["safety"]["manual_external_execution_only"] is True,
        "simulation_only": report["safety"]["simulation_only"] is True,
        "no_real_trade_or_broker": report["safety"]["no_real_trade"] is True
        and report["safety"]["no_broker_api"] is True,
        "no_webhook_or_secrets": report["safety"]["no_webhook"] is True
        and report["safety"]["no_secret_storage"] is True,
        "no_production_records_mutation": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.1-C acceptance checks failed: " + ", ".join(failed))

    report["checks"] = checks
    report["hashes"] = {
        "embedded_sandbox_json": _sha256(sandbox_json),
        "opportunities_json": _sha256(opportunities_json),
        "suggestions_json": _sha256(suggestions_json),
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
                "# V2.1-C Suggestion Gate Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- suggestions_json: `{report['suggestions_json']}`",
                f"- allowed_count: `{report['summary']['allowed_count']}`",
                f"- blocked_count: `{report['summary']['blocked_count']}`",
                "- safety: simulation only, manual external execution only, no real trade, no broker API",
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
                "target=V2.1-C Suggestion Gate",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                f"suggestions_json={report['suggestions_json']}",
                f"suggestions_json_sha256={report['hashes']['suggestions_json']}",
                "network_used=false",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
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
                    "target=V2.1-C Suggestion Gate",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.1-C Suggestion Gate FAIL: {exc}")
        return 1

    print(f"V2.1-C Suggestion Gate PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

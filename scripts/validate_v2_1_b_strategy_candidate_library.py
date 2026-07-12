#!/usr/bin/env python3
"""Validate Project Aegis V2.1-B Strategy Candidate Library."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.library import (  # noqa: E402
    StrategyCandidateLibrary,
    StrategyLibraryError,
    default_strategy_candidates,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_1_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_1_B_STRATEGY_CANDIDATE_LIBRARY_PASS.marker"
FAIL_MARKER = "V2_1_B_STRATEGY_CANDIDATE_LIBRARY_FAIL.marker"
REPORT_JSON = "v2_1_b_strategy_candidate_library_latest.json"
REPORT_MD = "v2_1_b_strategy_candidate_library_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_1_b_strategy_library_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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

    library_path = run_dir / "strategy_candidate_library.json"
    library = StrategyCandidateLibrary(library_path)
    candidates = default_strategy_candidates(created_at="2026-07-11T00:00:00+08:00")
    payload = library.save(candidates)
    loaded = library.load()

    duplicate_rejected = False
    try:
        library.save([*candidates, candidates[0]])
    except StrategyLibraryError:
        duplicate_rejected = True
        library.save(candidates)

    by_market = {
        "A": [candidate.strategy_id for candidate in library.list_by_market("A")],
        "H": [candidate.strategy_id for candidate in library.list_by_market("H")],
        "US": [candidate.strategy_id for candidate in library.list_by_market("US")],
    }
    multi_factor_ids = [candidate.strategy_id for candidate in library.list_by_factor_family("multi_factor")]
    overlay = library.get("portfolio_risk_veto_overlay")

    checks = {
        "library_written": library_path.exists(),
        "schema_version_present": payload["schema_version"] == "strategy_candidate_library.v1",
        "candidate_count": len(loaded) == 4,
        "a_h_us_coverage": bool(by_market["A"]) and bool(by_market["H"]) and bool(by_market["US"]),
        "risk_overlay_present": overlay.factor_family == "risk_overlay",
        "duplicate_rejected": duplicate_rejected,
        "market_filter_works": by_market["A"] == ["value_quality_defensive_a"]
        and by_market["H"] == ["low_volatility_dividend_h"],
        "factor_filter_works": len(multi_factor_ids) == 3,
        "simulation_only": payload["safety"]["simulation_only"] is True,
        "no_real_trade_or_broker": payload["safety"]["no_real_trade"] is True
        and payload["safety"]["no_broker_api"] is True,
        "no_strategy_auto_mutation": payload["safety"]["no_strategy_auto_mutation"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.1-B acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.1-B Strategy Candidate Library",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "library_json": str(library_path),
        "checks": checks,
        "summary": {
            "candidate_count": len(loaded),
            "markets": by_market,
            "multi_factor_ids": multi_factor_ids,
            "risk_overlay_id": overlay.strategy_id,
            "next_gate_required": "V2.1-C Suggestion Gate",
        },
        "safety": payload["safety"]
        | {
            "no_secret_storage": True,
            "no_webhook": True,
            "suggestion_gate_still_required": True,
            "dashboard_contract_unchanged": True,
            "no_production_records_mutation": True,
        },
        "hashes": {
            "library_json": _sha256(library_path),
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
                "# V2.1-B Strategy Candidate Library Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- library_json: `{report['library_json']}`",
                f"- candidate_count: `{report['summary']['candidate_count']}`",
                f"- markets: `{', '.join(report['summary']['markets'].keys())}`",
                "- safety: simulation only, no real trade, no broker API, no webhook, no strategy auto-mutation",
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
                "target=V2.1-B Strategy Candidate Library",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                f"library_json={report['library_json']}",
                f"library_json_sha256={report['hashes']['library_json']}",
                "network_used=false",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "simulation_only=true",
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
                    "target=V2.1-B Strategy Candidate Library",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.1-B Strategy Candidate Library FAIL: {exc}")
        return 1

    print(f"V2.1-B Strategy Candidate Library PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

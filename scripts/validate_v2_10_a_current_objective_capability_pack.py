from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis.operations.current_objective_pack import (
    build_current_objective_pack,
    render_current_objective_pack_markdown,
)


REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_10_a_acceptance"

CURRENT_BRIEF_JSON = ROOT / "data" / "processed" / "v2_9_h_acceptance" / "v2_9_h_20260711_acceptance" / "current_usable_simulation_brief.json"
LIVE_PUBLIC_SOURCE_AUDIT_JSON = ROOT / "data" / "reports" / "v2_8_b_live_public_strategy_source_audit_latest.json"
API_CANDIDATE_DRY_RUN_JSON = ROOT / "data" / "reports" / "v2_8_j_real_user_api_candidate_refresh_dry_run_latest.json"
HISTORICAL_SANDBOX_JSON = ROOT / "data" / "reports" / "v2_4_c_historical_sandbox_research_hypotheses_latest.json"
REFRESH_SANDBOX_JSON = ROOT / "data" / "reports" / "v2_8_d_refresh_queue_historical_sandbox_latest.json"
STRATEGY_SOURCE_CATALOG_JSON = ROOT / "data" / "reports" / "v2_4_a_strategy_research_source_catalog_latest.json"

PASS_MARKER = "V2_10_A_CURRENT_OBJECTIVE_CAPABILITY_PACK_PASS.marker"
FAIL_MARKER = "V2_10_A_CURRENT_OBJECTIVE_CAPABILITY_PACK_FAIL.marker"
REPORT_JSON = "v2_10_a_current_objective_capability_pack_latest.json"
REPORT_MD = "v2_10_a_current_objective_capability_pack_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_10_a_20260711_acceptance",
    command: str | None = None,
    current_brief_json: Path = CURRENT_BRIEF_JSON,
    live_public_source_audit_json: Path = LIVE_PUBLIC_SOURCE_AUDIT_JSON,
    api_candidate_dry_run_json: Path = API_CANDIDATE_DRY_RUN_JSON,
    historical_sandbox_json: Path = HISTORICAL_SANDBOX_JSON,
    refresh_sandbox_json: Path = REFRESH_SANDBOX_JSON,
    strategy_source_catalog_json: Path = STRATEGY_SOURCE_CATALOG_JSON,
) -> dict:
    inputs = {
        "current_brief_json": current_brief_json,
        "live_public_source_audit_json": live_public_source_audit_json,
        "api_candidate_dry_run_json": api_candidate_dry_run_json,
        "historical_sandbox_json": historical_sandbox_json,
        "refresh_sandbox_json": refresh_sandbox_json,
        "strategy_source_catalog_json": strategy_source_catalog_json,
    }
    missing = {name: str(path) for name, path in inputs.items() if not path.exists()}
    if missing:
        pack = {
            "overall_status": "FAIL",
            "acceptance_target": "V2.10-A Current Objective Capability Pack",
            "run_id": run_id,
            "generated_at": _now_iso(),
            "command": command,
            "missing_inputs": missing,
            "checks": {"all_inputs_present": False},
            "safety": {
                "simulation_only": True,
                "no_real_trade": True,
                "no_broker_api": True,
                "no_trading_webhook": True,
                "no_order_placement": True,
            },
        }
    else:
        pack = build_current_objective_pack(
            current_brief=_read_json(current_brief_json),
            live_public_source_audit=_read_json(live_public_source_audit_json),
            api_candidate_dry_run=_read_json(api_candidate_dry_run_json),
            historical_sandbox=_read_json(historical_sandbox_json),
            refresh_sandbox=_read_json(refresh_sandbox_json),
            strategy_source_catalog=_read_json(strategy_source_catalog_json),
            run_id=run_id,
            command=command,
        )
        pack["generated_at"] = _now_iso()
        pack["input_hashes"] = {name: _sha256(path) for name, path in inputs.items()}

    run_dir = output_root / run_id
    run_pack_json = run_dir / "current_objective_capability_pack.json"
    run_pack_md = run_dir / "current_objective_capability_pack.md"
    _write_json(run_pack_json, pack)
    run_pack_md.write_text(render_current_objective_pack_markdown(pack) if pack["overall_status"] == "PASS" else "# Project Aegis 当前目标能力包\n\nFAIL\n", encoding="utf-8")

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, pack)
    report_md.write_text(run_pack_md.read_text(encoding="utf-8"), encoding="utf-8")

    marker_name = PASS_MARKER if pack["overall_status"] == "PASS" else FAIL_MARKER
    stale_marker = reports_dir / (FAIL_MARKER if marker_name == PASS_MARKER else PASS_MARKER)
    if stale_marker.exists():
        stale_marker.unlink()
    (reports_dir / marker_name).write_text(
        json.dumps(
            {
                "status": pack["overall_status"],
                "acceptance_target": pack["acceptance_target"],
                "run_id": run_id,
                "report_json": str(report_json),
                "generated_at": pack["generated_at"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="v2_10_a_20260711_acceptance")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args(argv)
    command = " ".join(["validate_v2_10_a_current_objective_capability_pack.py", *(argv or [])])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
    )
    print(
        "V2.10-A Current Objective Capability Pack",
        report["overall_status"],
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

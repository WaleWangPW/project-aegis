from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis.external_sources.api_candidate_live_dry_run import run_api_candidate_live_dry_run  # noqa: E402
from aegis.external_sources.api_metadata_intake import CANDIDATE_REFRESH_CONNECTOR_ID  # noqa: E402


REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_10_c_acceptance"
LOCAL_CONFIG = ROOT / "config" / "external_api_connectors.local.json"
GITIGNORE = ROOT / ".gitignore"
SUGGESTION_DRAFTS_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_8_e_acceptance"
    / "v2_8_e_20260711_acceptance"
    / "refresh_queue_suggestion_drafts.json"
)

PASS_MARKER = "V2_10_C_REAL_API_CANDIDATE_REFRESH_LIVE_DRY_RUN_PASS.marker"
FAIL_MARKER = "V2_10_C_REAL_API_CANDIDATE_REFRESH_LIVE_DRY_RUN_FAIL.marker"
REPORT_JSON = "v2_10_c_real_api_candidate_refresh_live_dry_run_latest.json"
REPORT_MD = "v2_10_c_real_api_candidate_refresh_live_dry_run_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.10-C Real API Candidate Refresh Live Dry Run",
        "",
        f"- status: `{report['overall_status']}`",
        f"- dry_run_status: `{report['dry_run_status']}`",
        f"- intake_status: `{report['intake']['intake_status']}`",
        f"- network_used: `{report['network_used']}`",
        f"- blocked_by: `{', '.join(report['intake']['blocked_by']) or 'none'}`",
        "",
        "## Artifacts",
        "",
        f"- api_fetch_item_json: `{report['api_fetch_item_json']}`",
        f"- api_candidate_source_registry_json: `{report['api_candidate_source_registry_json']}`",
        f"- api_candidate_bindings_json: `{report['api_candidate_bindings_json']}`",
        "",
        "## Boundary",
        "",
        "- Activation gate before fetch.",
        "- Summary/hash and candidate summaries only.",
        "- Raw payload, request headers, query values, and env values are not stored.",
        "- No broker API, trading webhook, order placement, or production record mutation.",
        "",
    ]
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_10_c_20260711_acceptance",
    command: str | None = None,
    local_config_path: Path = LOCAL_CONFIG,
    gitignore_path: Path = GITIGNORE,
    suggestion_drafts_json: Path = SUGGESTION_DRAFTS_JSON,
    connector_id: str = CANDIDATE_REFRESH_CONNECTOR_ID,
    env: dict[str, str] | None = None,
    fetch_fn=None,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    live_run_dir = run_dir / "real_api_candidate_refresh_live_dry_run"

    report = run_api_candidate_live_dry_run(
        local_config_path=local_config_path,
        gitignore_path=gitignore_path,
        suggestion_drafts_json=suggestion_drafts_json,
        output_dir=live_run_dir,
        run_id=run_id,
        connector_id=connector_id,
        env=env if env is not None else os.environ,
        fetch_fn=fetch_fn,
        command=command,
    )
    report["generated_at"] = _now_iso()
    report["local_config_sha256"] = _sha256(local_config_path)
    report["suggestion_drafts_sha256"] = _sha256(suggestion_drafts_json)

    run_report_json = run_dir / "real_api_candidate_refresh_live_dry_run_report.json"
    run_report_md = run_dir / "real_api_candidate_refresh_live_dry_run_report.md"
    _write_json(run_report_json, report)
    run_report_md.write_text(_render_markdown(report), encoding="utf-8")

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(run_report_md.read_text(encoding="utf-8"), encoding="utf-8")

    marker_name = PASS_MARKER if report["overall_status"] == "PASS" else FAIL_MARKER
    stale = reports_dir / (FAIL_MARKER if marker_name == PASS_MARKER else PASS_MARKER)
    if stale.exists():
        stale.unlink()
    (reports_dir / marker_name).write_text(
        json.dumps(
            {
                "status": report["overall_status"],
                "acceptance_target": report["acceptance_target"],
                "run_id": run_id,
                "report_json": str(report_json),
                "generated_at": report["generated_at"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="v2_10_c_20260711_acceptance")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--local-config-path", type=Path, default=LOCAL_CONFIG)
    parser.add_argument("--suggestion-drafts-json", type=Path, default=SUGGESTION_DRAFTS_JSON)
    parser.add_argument("--connector-id", default=CANDIDATE_REFRESH_CONNECTOR_ID)
    args = parser.parse_args(argv)
    command = " ".join(["validate_v2_10_c_real_api_candidate_refresh_live_dry_run.py", *(argv or [])])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        local_config_path=args.local_config_path,
        suggestion_drafts_json=args.suggestion_drafts_json,
        connector_id=args.connector_id,
    )
    print(
        "V2.10-C Real API Candidate Refresh Live Dry Run",
        report["overall_status"],
        f"dry_run_status={report['dry_run_status']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

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

from aegis.external_sources.api_metadata_intake import (  # noqa: E402
    CANDIDATE_REFRESH_CONNECTOR_ID,
    build_api_metadata_intake_report,
)


REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_10_b_acceptance"
LOCAL_CONFIG = ROOT / "config" / "external_api_connectors.local.json"
GITIGNORE = ROOT / ".gitignore"

PASS_MARKER = "V2_10_B_REAL_API_METADATA_INTAKE_PASS.marker"
FAIL_MARKER = "V2_10_B_REAL_API_METADATA_INTAKE_FAIL.marker"
REPORT_JSON = "v2_10_b_real_api_metadata_intake_latest.json"
REPORT_MD = "v2_10_b_real_api_metadata_intake_latest.md"


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
    intake = report["intake"]
    lines = [
        "# V2.10-B Real API Metadata Intake",
        "",
        f"- status: `{report['overall_status']}`",
        f"- intake_status: `{intake['intake_status']}`",
        f"- connector_id: `{report['summary']['connector_id']}`",
        f"- blocked_by: `{', '.join(report['summary']['blocked_by']) or 'none'}`",
        f"- required_env_vars: `{report['summary']['required_env_vars']}`",
        f"- present_env_vars: `{report['summary']['present_env_vars']}`",
        f"- missing_env_vars: `{report['summary']['missing_env_vars']}`",
        "",
        "## What This Means",
        "",
    ]
    if intake["intake_status"] == "blocked_missing_metadata":
        lines.append("- Create `config/external_api_connectors.local.json` from `config/external_api_connectors.user-template.json` and fill non-secret metadata only.")
    elif intake["intake_status"] == "blocked_missing_env_vars":
        lines.append("- Metadata is present, but required local env vars are missing. Set env vars locally; do not write values into repo or Vault.")
    elif intake["intake_status"] == "ready_for_live_readiness_check":
        lines.append("- Metadata and env var names are ready for the next bounded live API dry-run gate.")
    else:
        lines.append("- Metadata is present but needs cleanup before live readiness can proceed.")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Metadata preflight only.",
            "- No network fetch.",
            "- No raw config copy stored.",
            "- Env var names only; env values are never serialized.",
            "- No broker API, trading webhook, order placement, or production record mutation.",
            "",
        ]
    )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_10_b_20260711_acceptance",
    command: str | None = None,
    local_config_path: Path = LOCAL_CONFIG,
    gitignore_path: Path = GITIGNORE,
    connector_id: str = CANDIDATE_REFRESH_CONNECTOR_ID,
    env: dict[str, str] | None = None,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = build_api_metadata_intake_report(
        local_config_path=local_config_path,
        gitignore_path=gitignore_path,
        connector_id=connector_id,
        run_id=run_id,
        env=env if env is not None else os.environ,
        command=command,
    )
    report["local_config_sha256"] = _sha256(local_config_path)
    report["gitignore_sha256"] = _sha256(gitignore_path)
    report["generated_at"] = _now_iso()

    run_report_json = run_dir / "real_api_metadata_intake_report.json"
    run_report_md = run_dir / "real_api_metadata_intake_report.md"
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
    parser.add_argument("--run-id", default="v2_10_b_20260711_acceptance")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--local-config-path", type=Path, default=LOCAL_CONFIG)
    parser.add_argument("--connector-id", default=CANDIDATE_REFRESH_CONNECTOR_ID)
    args = parser.parse_args(argv)
    command = " ".join(["validate_v2_10_b_real_api_metadata_intake.py", *(argv or [])])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        local_config_path=args.local_config_path,
        connector_id=args.connector_id,
    )
    print(
        "V2.10-B Real API Metadata Intake",
        report["overall_status"],
        f"intake_status={report['summary']['intake_status']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

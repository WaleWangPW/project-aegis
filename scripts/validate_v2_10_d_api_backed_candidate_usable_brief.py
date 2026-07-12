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

from aegis.external_sources.api_backed_brief import (  # noqa: E402
    build_api_backed_candidate_brief,
    render_api_backed_candidate_brief_markdown,
)


REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_10_d_acceptance"
LIVE_DRY_RUN_REPORT = ROOT / "data" / "reports" / "v2_10_c_real_api_candidate_refresh_live_dry_run_latest.json"
SUGGESTION_DRAFTS_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_8_e_acceptance"
    / "v2_8_e_20260711_acceptance"
    / "refresh_queue_suggestion_drafts.json"
)

PASS_MARKER = "V2_10_D_API_BACKED_CANDIDATE_USABLE_BRIEF_PASS.marker"
FAIL_MARKER = "V2_10_D_API_BACKED_CANDIDATE_USABLE_BRIEF_FAIL.marker"
REPORT_JSON = "v2_10_d_api_backed_candidate_usable_brief_latest.json"
REPORT_MD = "v2_10_d_api_backed_candidate_usable_brief_latest.md"


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


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_10_d_20260711_acceptance",
    command: str | None = None,
    live_dry_run_report_json: Path = LIVE_DRY_RUN_REPORT,
    suggestion_drafts_json: Path = SUGGESTION_DRAFTS_JSON,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    live_report = json.loads(live_dry_run_report_json.read_text(encoding="utf-8"))
    report = build_api_backed_candidate_brief(
        live_dry_run_report=live_report,
        suggestion_drafts_json=suggestion_drafts_json,
        run_id=run_id,
        evidence_refs=[str(live_dry_run_report_json)],
    )
    report["generated_at"] = _now_iso()
    report["command"] = command
    report["source_live_dry_run_report_json"] = str(live_dry_run_report_json)
    report["source_suggestion_drafts_json"] = str(suggestion_drafts_json)
    report["hashes"] = {
        "source_live_dry_run_report_json": _sha256(live_dry_run_report_json),
        "source_suggestion_drafts_json": _sha256(suggestion_drafts_json),
    }

    run_report_json = run_dir / "api_backed_candidate_usable_brief.json"
    run_report_md = run_dir / "api_backed_candidate_usable_brief.md"
    _write_json(run_report_json, report)
    run_report_md.write_text(render_api_backed_candidate_brief_markdown(report), encoding="utf-8")
    report["brief_json"] = str(run_report_json)
    report["brief_md"] = str(run_report_md)
    report["hashes"]["brief_json"] = _sha256(run_report_json)
    report["hashes"]["brief_md"] = _sha256(run_report_md)
    _write_json(run_report_json, report)

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
                "brief_status": report.get("brief_status"),
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
    parser.add_argument("--run-id", default="v2_10_d_20260711_acceptance")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--live-dry-run-report-json", type=Path, default=LIVE_DRY_RUN_REPORT)
    parser.add_argument("--suggestion-drafts-json", type=Path, default=SUGGESTION_DRAFTS_JSON)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join(["validate_v2_10_d_api_backed_candidate_usable_brief.py", *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        live_dry_run_report_json=args.live_dry_run_report_json,
        suggestion_drafts_json=args.suggestion_drafts_json,
    )
    print(
        "V2.10-D API-Backed Candidate Usable Brief",
        report["overall_status"],
        f"brief_status={report.get('brief_status')}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

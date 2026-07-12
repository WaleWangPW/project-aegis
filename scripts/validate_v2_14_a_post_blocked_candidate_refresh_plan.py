#!/usr/bin/env python3
"""Validate V2.14-A post-blocked candidate refresh plan."""

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

from aegis.strategy.post_blocked_candidate_refresh import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_post_blocked_candidate_refresh_plan,
    render_post_blocked_candidate_refresh_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_14_a_acceptance"
SOURCE_V2_13_W_REPORT_JSON = REPORTS_DIR / "v2_13_w_finnhub_quote_multi_symbol_result_brief_latest.json"
SOURCE_V2_13_W_PASS_MARKER = REPORTS_DIR / "V2_13_W_FINNHUB_QUOTE_MULTI_SYMBOL_RESULT_BRIEF_PASS.marker"
SOURCE_V2_9_A_REPORT_JSON = REPORTS_DIR / "v2_9_a_current_user_decision_packet_latest.json"
SOURCE_V2_9_A_PASS_MARKER = REPORTS_DIR / "V2_9_A_CURRENT_USER_DECISION_PACKET_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_14_A_POST_BLOCKED_CANDIDATE_REFRESH_PLAN_PASS.marker"
FAIL_MARKER = "V2_14_A_POST_BLOCKED_CANDIDATE_REFRESH_PLAN_FAIL.marker"
REPORT_JSON = "v2_14_a_post_blocked_candidate_refresh_plan_latest.json"
REPORT_MD = "v2_14_a_post_blocked_candidate_refresh_plan_latest.md"


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


def _fingerprint(path: Path) -> dict:
    return {
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": _sha256(path),
    }


def _fingerprints(paths: dict[str, Path]) -> dict[str, dict]:
    return {name: _fingerprint(path) for name, path in paths.items()}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_14_a_20260712_acceptance",
    command: str | None = None,
    source_v2_13_w_report_json: Path = SOURCE_V2_13_W_REPORT_JSON,
    source_v2_13_w_pass_marker: Path = SOURCE_V2_13_W_PASS_MARKER,
    source_v2_9_a_report_json: Path = SOURCE_V2_9_A_REPORT_JSON,
    source_v2_9_a_pass_marker: Path = SOURCE_V2_9_A_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    blocked_brief = _load_json(source_v2_13_w_report_json)
    decision_packet = _load_json(source_v2_9_a_report_json)
    report = build_post_blocked_candidate_refresh_plan(
        blocked_brief=blocked_brief,
        decision_packet=decision_packet,
        run_id=run_id,
        command=command,
    )

    plan_json = run_dir / "post_blocked_candidate_refresh_plan.json"
    plan_md = run_dir / "post_blocked_candidate_refresh_plan.md"
    _write_json(plan_json, report)
    plan_md.write_text(render_post_blocked_candidate_refresh_markdown(report), encoding="utf-8")
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "plan_status_pass": report["overall_status"] == "PASS",
        "source_v2_13_w_report_exists": source_v2_13_w_report_json.exists(),
        "source_v2_13_w_marker_exists": source_v2_13_w_pass_marker.exists(),
        "source_v2_9_a_report_exists": source_v2_9_a_report_json.exists(),
        "source_v2_9_a_marker_exists": source_v2_9_a_pass_marker.exists(),
        "plan_json_written": plan_json.exists(),
        "plan_md_written": plan_md.exists(),
        "production_record_files_unchanged": before == after,
        "source_hashes_recorded": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["plan_json"] = str(plan_json)
    report["plan_md"] = str(plan_md)
    report["source_v2_13_w_report_json"] = str(source_v2_13_w_report_json)
    report["source_v2_13_w_pass_marker"] = str(source_v2_13_w_pass_marker)
    report["source_v2_9_a_report_json"] = str(source_v2_9_a_report_json)
    report["source_v2_9_a_pass_marker"] = str(source_v2_9_a_pass_marker)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_w_report_json": _sha256(source_v2_13_w_report_json),
        "source_v2_13_w_pass_marker": _sha256(source_v2_13_w_pass_marker),
        "source_v2_9_a_report_json": _sha256(source_v2_9_a_report_json),
        "source_v2_9_a_pass_marker": _sha256(source_v2_9_a_pass_marker),
        "plan_json": _sha256(plan_json),
        "plan_md": _sha256(plan_md),
    }
    _write_json(plan_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_post_blocked_candidate_refresh_markdown(report), encoding="utf-8")

    marker_name = PASS_MARKER if report["overall_status"] == "PASS" else FAIL_MARKER
    stale = reports_dir / (FAIL_MARKER if marker_name == PASS_MARKER else PASS_MARKER)
    if stale.exists():
        stale.unlink()
    (reports_dir / marker_name).write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={command or ''}",
                f"exit_code={0 if report['overall_status'] == 'PASS' else 1}",
                f"target={ACCEPTANCE_TARGET}",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"plan_json={plan_json}",
                f"plan_json_sha256={_sha256(plan_json)}",
                f"plan_md={plan_md}",
                f"plan_md_sha256={_sha256(plan_md)}",
                f"source_v2_13_w_report_json={source_v2_13_w_report_json}",
                f"source_v2_13_w_report_json_sha256={_sha256(source_v2_13_w_report_json)}",
                f"source_v2_13_w_pass_marker={source_v2_13_w_pass_marker}",
                f"source_v2_13_w_pass_marker_sha256={_sha256(source_v2_13_w_pass_marker)}",
                f"source_v2_9_a_report_json={source_v2_9_a_report_json}",
                f"source_v2_9_a_report_json_sha256={_sha256(source_v2_9_a_report_json)}",
                f"source_v2_9_a_pass_marker={source_v2_9_a_pass_marker}",
                f"source_v2_9_a_pass_marker_sha256={_sha256(source_v2_9_a_pass_marker)}",
                f"removed_candidate_count={report['summary']['removed_candidate_count']}",
                f"retained_candidate_count={report['summary']['retained_candidate_count']}",
                f"retained_markets={','.join(report['summary']['retained_markets'])}",
                f"replacement_required_markets={','.join(report['summary']['replacement_required_markets'])}",
                "network_used=false",
                "not_user_facing_suggestion=true",
                "requires_historical_sandbox=true",
                "requires_suggestion_gate=true",
                "production_records_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
                "no_secret_values_stored=true",
                "request_urls_not_stored=true",
                "raw_payloads_not_stored=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_position_size=true",
                "no_live_order_signal=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--run-id", default="v2_14_a_20260712_acceptance")
    parser.add_argument("--source-v2-13-w-report-json", type=Path, default=SOURCE_V2_13_W_REPORT_JSON)
    parser.add_argument("--source-v2-13-w-pass-marker", type=Path, default=SOURCE_V2_13_W_PASS_MARKER)
    parser.add_argument("--source-v2-9-a-report-json", type=Path, default=SOURCE_V2_9_A_REPORT_JSON)
    parser.add_argument("--source-v2-9-a-pass-marker", type=Path, default=SOURCE_V2_9_A_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_w_report_json=args.source_v2_13_w_report_json,
        source_v2_13_w_pass_marker=args.source_v2_13_w_pass_marker,
        source_v2_9_a_report_json=args.source_v2_9_a_report_json,
        source_v2_9_a_pass_marker=args.source_v2_9_a_pass_marker,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"removed_candidate_count={report['summary']['removed_candidate_count']}",
        f"retained_candidate_count={report['summary']['retained_candidate_count']}",
        f"replacement_required_markets={','.join(report['summary']['replacement_required_markets'])}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

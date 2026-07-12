#!/usr/bin/env python3
"""Validate V2.13-Q Finnhub quote multi-symbol expansion plan."""

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

from aegis.external_sources.finnhub_quote_multi_symbol_expansion import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_multi_symbol_expansion_plan,
    render_finnhub_quote_multi_symbol_expansion_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_q_acceptance"
SOURCE_V2_13_P_REPORT_JSON = REPORTS_DIR / "v2_13_p_finnhub_quote_brief_review_memory_refresh_latest.json"
SOURCE_V2_13_P_PASS_MARKER = REPORTS_DIR / "V2_13_P_FINNHUB_QUOTE_BRIEF_REVIEW_MEMORY_REFRESH_PASS.marker"
SOURCE_V2_9_A_DECISION_PACKET_JSON = REPORTS_DIR / "v2_9_a_current_user_decision_packet_latest.json"
SOURCE_V2_9_A_PASS_MARKER = REPORTS_DIR / "V2_9_A_CURRENT_USER_DECISION_PACKET_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_Q_FINNHUB_QUOTE_MULTI_SYMBOL_EXPANSION_PLAN_PASS.marker"
FAIL_MARKER = "V2_13_Q_FINNHUB_QUOTE_MULTI_SYMBOL_EXPANSION_PLAN_FAIL.marker"
REPORT_JSON = "v2_13_q_finnhub_quote_multi_symbol_expansion_plan_latest.json"
REPORT_MD = "v2_13_q_finnhub_quote_multi_symbol_expansion_plan_latest.md"


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
    run_id: str = "v2_13_q_20260712_acceptance",
    command: str | None = None,
    source_v2_13_p_report_json: Path = SOURCE_V2_13_P_REPORT_JSON,
    source_v2_13_p_pass_marker: Path = SOURCE_V2_13_P_PASS_MARKER,
    source_v2_9_a_decision_packet_json: Path = SOURCE_V2_9_A_DECISION_PACKET_JSON,
    source_v2_9_a_pass_marker: Path = SOURCE_V2_9_A_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    refresh_report = _load_json(source_v2_13_p_report_json)
    decision_packet = _load_json(source_v2_9_a_decision_packet_json)
    report = build_finnhub_quote_multi_symbol_expansion_plan(
        refresh_report,
        decision_packet,
        run_id=run_id,
        command=command,
    )

    plan_json = run_dir / "finnhub_quote_multi_symbol_expansion_plan.json"
    plan_md = run_dir / "finnhub_quote_multi_symbol_expansion_plan.md"
    probe_queue_json = run_dir / "finnhub_quote_symbol_probe_queue.json"
    provider_queue_json = run_dir / "provider_routed_candidate_expansion_queue.json"
    _write_json(plan_json, report)
    plan_md.write_text(render_finnhub_quote_multi_symbol_expansion_markdown(report), encoding="utf-8")
    _write_json(probe_queue_json, {"items": report["finnhub_probe_queue"]})
    _write_json(provider_queue_json, {"items": report["queue_items"], "provider_routes": report["provider_routes"]})
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "report_status_pass": report["overall_status"] == "PASS",
        "source_v2_13_p_marker_exists": source_v2_13_p_pass_marker.exists(),
        "source_v2_9_a_marker_exists": source_v2_9_a_pass_marker.exists(),
        "plan_json_written": plan_json.exists(),
        "plan_md_written": plan_md.exists(),
        "probe_queue_json_written": probe_queue_json.exists(),
        "provider_queue_json_written": provider_queue_json.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "network_not_used": report["network_used"] is False,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["plan_json"] = str(plan_json)
    report["plan_md"] = str(plan_md)
    report["probe_queue_json"] = str(probe_queue_json)
    report["provider_queue_json"] = str(provider_queue_json)
    report["source_v2_13_p_report_json"] = str(source_v2_13_p_report_json)
    report["source_v2_13_p_pass_marker"] = str(source_v2_13_p_pass_marker)
    report["source_v2_9_a_decision_packet_json"] = str(source_v2_9_a_decision_packet_json)
    report["source_v2_9_a_pass_marker"] = str(source_v2_9_a_pass_marker)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_p_report_json": _sha256(source_v2_13_p_report_json),
        "source_v2_13_p_pass_marker": _sha256(source_v2_13_p_pass_marker),
        "source_v2_9_a_decision_packet_json": _sha256(source_v2_9_a_decision_packet_json),
        "source_v2_9_a_pass_marker": _sha256(source_v2_9_a_pass_marker),
        "plan_json": _sha256(plan_json),
        "plan_md": _sha256(plan_md),
        "probe_queue_json": _sha256(probe_queue_json),
        "provider_queue_json": _sha256(provider_queue_json),
    }
    _write_json(plan_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_finnhub_quote_multi_symbol_expansion_markdown(report), encoding="utf-8")

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
                f"probe_queue_json={probe_queue_json}",
                f"probe_queue_json_sha256={_sha256(probe_queue_json)}",
                f"provider_queue_json={provider_queue_json}",
                f"provider_queue_json_sha256={_sha256(provider_queue_json)}",
                f"source_v2_13_p_report_json={source_v2_13_p_report_json}",
                f"source_v2_13_p_report_json_sha256={_sha256(source_v2_13_p_report_json)}",
                f"source_v2_9_a_decision_packet_json={source_v2_9_a_decision_packet_json}",
                f"source_v2_9_a_decision_packet_json_sha256={_sha256(source_v2_9_a_decision_packet_json)}",
                f"candidate_count={report['summary']['candidate_count']}",
                f"finnhub_probe_queue_count={report['summary']['finnhub_probe_queue_count']}",
                f"finnhub_probe_symbols={','.join(str(x) for x in report['summary']['finnhub_probe_symbols'])}",
                f"already_context_symbols={','.join(str(x) for x in report['summary']['already_context_symbols'])}",
                f"routed_away_symbols={','.join(str(x) for x in report['summary']['routed_away_symbols'])}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "social_sentiment_not_enabled=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_live_price=true",
                "no_position_size=true",
                "no_live_order_signal=true",
                "no_strategy_mutation=true",
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
    parser.add_argument("--run-id", default="v2_13_q_20260712_acceptance")
    parser.add_argument("--source-v2-13-p-report-json", type=Path, default=SOURCE_V2_13_P_REPORT_JSON)
    parser.add_argument("--source-v2-13-p-pass-marker", type=Path, default=SOURCE_V2_13_P_PASS_MARKER)
    parser.add_argument("--source-v2-9-a-decision-packet-json", type=Path, default=SOURCE_V2_9_A_DECISION_PACKET_JSON)
    parser.add_argument("--source-v2-9-a-pass-marker", type=Path, default=SOURCE_V2_9_A_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_p_report_json=args.source_v2_13_p_report_json,
        source_v2_13_p_pass_marker=args.source_v2_13_p_pass_marker,
        source_v2_9_a_decision_packet_json=args.source_v2_9_a_decision_packet_json,
        source_v2_9_a_pass_marker=args.source_v2_9_a_pass_marker,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"candidate_count={report['summary']['candidate_count']}",
        f"finnhub_probe_queue_count={report['summary']['finnhub_probe_queue_count']}",
        f"symbols={','.join(str(x) for x in report['summary']['finnhub_probe_symbols'])}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

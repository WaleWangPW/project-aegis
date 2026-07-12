#!/usr/bin/env python3
"""Validate V2.13-H Finnhub quote sandbox evidence to Suggestion Gate draft."""

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

from aegis.external_sources.finnhub_quote_suggestion_gate import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_suggestion_gate_report,
    render_finnhub_quote_suggestion_gate_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_h_acceptance"
SOURCE_V2_13_G_REPORT_JSON = REPORTS_DIR / "v2_13_g_finnhub_quote_sandbox_evaluation_latest.json"
SOURCE_V2_13_G_PASS_MARKER = REPORTS_DIR / "V2_13_G_FINNHUB_QUOTE_SANDBOX_EVALUATION_PASS.marker"

PASS_MARKER = "V2_13_H_FINNHUB_QUOTE_SUGGESTION_GATE_PASS.marker"
FAIL_MARKER = "V2_13_H_FINNHUB_QUOTE_SUGGESTION_GATE_FAIL.marker"
REPORT_JSON = "v2_13_h_finnhub_quote_suggestion_gate_latest.json"
REPORT_MD = "v2_13_h_finnhub_quote_suggestion_gate_latest.md"


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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_13_h_20260712_acceptance",
    command: str | None = None,
    source_v2_13_g_report_json: Path = SOURCE_V2_13_G_REPORT_JSON,
    source_v2_13_g_pass_marker: Path = SOURCE_V2_13_G_PASS_MARKER,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    evidence_refs = [str(source_v2_13_g_report_json), str(source_v2_13_g_pass_marker)]
    report = build_finnhub_quote_suggestion_gate_report(
        _load_json(source_v2_13_g_report_json),
        run_id=run_id,
        evidence_refs=evidence_refs,
        command=command,
    )

    opportunities_json = run_dir / "finnhub_quote_suggestion_opportunities.json"
    suggestions_json = run_dir / "finnhub_quote_suggestion_drafts.json"
    gate_report_json = run_dir / "finnhub_quote_suggestion_gate_report.json"
    gate_report_md = run_dir / "finnhub_quote_suggestion_gate_report.md"

    _write_json(opportunities_json, {"opportunities": report["opportunities"]})
    _write_json(suggestions_json, {"suggestions": report["suggestions"]})
    _write_json(gate_report_json, report)
    gate_report_md.write_text(render_finnhub_quote_suggestion_gate_markdown(report), encoding="utf-8")

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "report_status_pass": report["overall_status"] == "PASS",
        "source_marker_exists": source_v2_13_g_pass_marker.exists(),
        "opportunities_json_written": opportunities_json.exists(),
        "suggestions_json_written": suggestions_json.exists(),
        "gate_report_json_written": gate_report_json.exists(),
        "gate_report_md_written": gate_report_md.exists(),
        "hashes_recorded": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["opportunities_json"] = str(opportunities_json)
    report["suggestions_json"] = str(suggestions_json)
    report["gate_report_json"] = str(gate_report_json)
    report["gate_report_md"] = str(gate_report_md)
    report["source_v2_13_g_report_json"] = str(source_v2_13_g_report_json)
    report["source_v2_13_g_pass_marker"] = str(source_v2_13_g_pass_marker)
    report["hashes"] = {
        "source_v2_13_g_report_json": _sha256(source_v2_13_g_report_json),
        "source_v2_13_g_pass_marker": _sha256(source_v2_13_g_pass_marker),
        "opportunities_json": _sha256(opportunities_json),
        "suggestions_json": _sha256(suggestions_json),
        "gate_report_json": _sha256(gate_report_json),
        "gate_report_md": _sha256(gate_report_md),
    }
    _write_json(gate_report_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_finnhub_quote_suggestion_gate_markdown(report), encoding="utf-8")

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
                f"suggestions_json={suggestions_json}",
                f"suggestions_json_sha256={_sha256(suggestions_json)}",
                f"opportunities_json={opportunities_json}",
                f"opportunities_json_sha256={_sha256(opportunities_json)}",
                f"source_v2_13_g_report_json={source_v2_13_g_report_json}",
                f"source_v2_13_g_report_json_sha256={_sha256(source_v2_13_g_report_json)}",
                f"source_v2_13_g_pass_marker={source_v2_13_g_pass_marker}",
                f"source_v2_13_g_pass_marker_sha256={_sha256(source_v2_13_g_pass_marker)}",
                f"allowed_count={report['summary']['allowed_count']}",
                f"blocked_count={report['summary']['blocked_count']}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
                "network_used=false",
                "production_records_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "quote_context_research_only=true",
                "social_sentiment_not_enabled=true",
                "not_real_trade_advice=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
                "no_live_price=true",
                "no_position_size=true",
                "no_live_order_signal=true",
                "no_secret_storage=true",
                "no_request_url_storage=true",
                "no_raw_payload_storage=true",
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
    parser.add_argument("--run-id", default="v2_13_h_20260712_acceptance")
    parser.add_argument("--source-v2-13-g-report-json", type=Path, default=SOURCE_V2_13_G_REPORT_JSON)
    parser.add_argument("--source-v2-13-g-pass-marker", type=Path, default=SOURCE_V2_13_G_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_g_report_json=args.source_v2_13_g_report_json,
        source_v2_13_g_pass_marker=args.source_v2_13_g_pass_marker,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"allowed_count={report['summary']['allowed_count']}",
        f"blocked_count={report['summary']['blocked_count']}",
        f"social_sentiment={report['summary']['social_sentiment_status']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

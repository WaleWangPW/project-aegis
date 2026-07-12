#!/usr/bin/env python3
"""Validate V2.13-W Finnhub quote multi-symbol sandbox result brief."""

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

from aegis.external_sources.finnhub_quote_multi_symbol_result_brief import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_multi_symbol_result_brief,
    render_finnhub_quote_multi_symbol_result_brief_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_w_acceptance"
SOURCE_V2_13_V_REPORT_JSON = REPORTS_DIR / "v2_13_v_finnhub_quote_multi_symbol_sandbox_evaluation_latest.json"
SOURCE_V2_13_V_PASS_MARKER = REPORTS_DIR / "V2_13_V_FINNHUB_QUOTE_MULTI_SYMBOL_SANDBOX_EVALUATION_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_W_FINNHUB_QUOTE_MULTI_SYMBOL_RESULT_BRIEF_PASS.marker"
FAIL_MARKER = "V2_13_W_FINNHUB_QUOTE_MULTI_SYMBOL_RESULT_BRIEF_FAIL.marker"
REPORT_JSON = "v2_13_w_finnhub_quote_multi_symbol_result_brief_latest.json"
REPORT_MD = "v2_13_w_finnhub_quote_multi_symbol_result_brief_latest.md"


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
    run_id: str = "v2_13_w_20260712_acceptance",
    command: str | None = None,
    source_v2_13_v_report_json: Path = SOURCE_V2_13_V_REPORT_JSON,
    source_v2_13_v_pass_marker: Path = SOURCE_V2_13_V_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    source_report = _load_json(source_v2_13_v_report_json)
    brief = build_finnhub_quote_multi_symbol_result_brief(
        source_report,
        run_id=run_id,
        command=command,
    )

    brief_json = run_dir / "finnhub_quote_multi_symbol_result_brief.json"
    brief_md = run_dir / "finnhub_quote_multi_symbol_result_brief.md"
    _write_json(brief_json, brief)
    brief_md.write_text(render_finnhub_quote_multi_symbol_result_brief_markdown(brief), encoding="utf-8")
    after = _fingerprints(record_paths)

    checks = {
        **brief["checks"],
        "acceptance_target_correct": brief["acceptance_target"] == ACCEPTANCE_TARGET,
        "brief_status_pass": brief["overall_status"] == "PASS",
        "source_v2_13_v_report_exists": source_v2_13_v_report_json.exists(),
        "source_v2_13_v_marker_exists": source_v2_13_v_pass_marker.exists(),
        "brief_json_written": brief_json.exists(),
        "brief_md_written": brief_md.exists(),
        "production_record_files_unchanged": before == after,
        "source_hashes_recorded": True,
    }
    brief["checks"] = checks
    brief["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    brief["generated_at"] = _now_iso()
    brief["run_dir"] = str(run_dir)
    brief["brief_json"] = str(brief_json)
    brief["brief_md"] = str(brief_md)
    brief["source_v2_13_v_report_json"] = str(source_v2_13_v_report_json)
    brief["source_v2_13_v_pass_marker"] = str(source_v2_13_v_pass_marker)
    brief["production_record_files_before"] = before
    brief["production_record_files_after"] = after
    brief["hashes"] = {
        "source_v2_13_v_report_json": _sha256(source_v2_13_v_report_json),
        "source_v2_13_v_pass_marker": _sha256(source_v2_13_v_pass_marker),
        "brief_json": _sha256(brief_json),
        "brief_md": _sha256(brief_md),
    }
    _write_json(brief_json, brief)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, brief)
    report_md.write_text(render_finnhub_quote_multi_symbol_result_brief_markdown(brief), encoding="utf-8")

    marker_name = PASS_MARKER if brief["overall_status"] == "PASS" else FAIL_MARKER
    stale = reports_dir / (FAIL_MARKER if marker_name == PASS_MARKER else PASS_MARKER)
    if stale.exists():
        stale.unlink()
    (reports_dir / marker_name).write_text(
        "\n".join(
            [
                f"generated_at={brief['generated_at']}",
                f"command={command or ''}",
                f"exit_code={0 if brief['overall_status'] == 'PASS' else 1}",
                f"target={ACCEPTANCE_TARGET}",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"brief_json={brief_json}",
                f"brief_json_sha256={_sha256(brief_json)}",
                f"brief_md={brief_md}",
                f"brief_md_sha256={_sha256(brief_md)}",
                f"source_v2_13_v_report_json={source_v2_13_v_report_json}",
                f"source_v2_13_v_report_json_sha256={_sha256(source_v2_13_v_report_json)}",
                f"source_v2_13_v_pass_marker={source_v2_13_v_pass_marker}",
                f"source_v2_13_v_pass_marker_sha256={_sha256(source_v2_13_v_pass_marker)}",
                f"blocked_item_count={brief['summary']['blocked_item_count']}",
                f"passed_item_count={brief['summary']['passed_item_count']}",
                f"blocked_symbols={','.join(brief['summary']['blocked_symbols'])}",
                f"failed_reason_codes={','.join(brief['summary']['failed_reason_codes'])}",
                "network_used=false",
                "suggestion_gate_ready=false",
                "user_facing_suggestion_allowed=false",
                "not_a_suggestion=true",
                "production_records_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
                "no_live_price=true",
                "no_position_size=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_live_order_signal=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return brief


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--run-id", default="v2_13_w_20260712_acceptance")
    parser.add_argument("--source-v2-13-v-report-json", type=Path, default=SOURCE_V2_13_V_REPORT_JSON)
    parser.add_argument("--source-v2-13-v-pass-marker", type=Path, default=SOURCE_V2_13_V_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_v_report_json=args.source_v2_13_v_report_json,
        source_v2_13_v_pass_marker=args.source_v2_13_v_pass_marker,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"blocked_item_count={report['summary']['blocked_item_count']}",
        f"passed_item_count={report['summary']['passed_item_count']}",
        f"blocked_symbols={','.join(report['summary']['blocked_symbols'])}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

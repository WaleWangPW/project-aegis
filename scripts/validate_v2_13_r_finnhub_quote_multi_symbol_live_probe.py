#!/usr/bin/env python3
"""Validate V2.13-R Finnhub quote multi-symbol live probe dry run."""

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

from aegis.external_sources.finnhub_quote_multi_symbol_live_probe import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_multi_symbol_live_probe_report,
    render_finnhub_quote_multi_symbol_live_probe_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_r_acceptance"
SOURCE_V2_13_Q_REPORT_JSON = REPORTS_DIR / "v2_13_q_finnhub_quote_multi_symbol_expansion_plan_latest.json"
SOURCE_V2_13_Q_PASS_MARKER = REPORTS_DIR / "V2_13_Q_FINNHUB_QUOTE_MULTI_SYMBOL_EXPANSION_PLAN_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_R_FINNHUB_QUOTE_MULTI_SYMBOL_LIVE_PROBE_PASS.marker"
FAIL_MARKER = "V2_13_R_FINNHUB_QUOTE_MULTI_SYMBOL_LIVE_PROBE_FAIL.marker"
REPORT_JSON = "v2_13_r_finnhub_quote_multi_symbol_live_probe_latest.json"
REPORT_MD = "v2_13_r_finnhub_quote_multi_symbol_live_probe_latest.md"


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
    run_id: str = "v2_13_r_20260712_acceptance",
    command: str | None = None,
    source_v2_13_q_report_json: Path = SOURCE_V2_13_Q_REPORT_JSON,
    source_v2_13_q_pass_marker: Path = SOURCE_V2_13_Q_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
    env: dict[str, str] | None = None,
    fetch_json=None,
) -> dict:
    run_dir = output_root / run_id
    normalized_quote_dir = run_dir / "normalized_quote_cache"
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    expansion_report = _load_json(source_v2_13_q_report_json)
    report = build_finnhub_quote_multi_symbol_live_probe_report(
        expansion_report,
        output_dir=normalized_quote_dir,
        run_id=run_id,
        command=command,
        env=env,
        fetch_json=fetch_json,
    )

    probe_json = run_dir / "finnhub_quote_multi_symbol_live_probe_report.json"
    probe_md = run_dir / "finnhub_quote_multi_symbol_live_probe_report.md"
    _write_json(probe_json, report)
    probe_md.write_text(render_finnhub_quote_multi_symbol_live_probe_markdown(report), encoding="utf-8")
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "report_status_pass": report["overall_status"] == "PASS",
        "source_v2_13_q_marker_exists": source_v2_13_q_pass_marker.exists(),
        "probe_json_written": probe_json.exists(),
        "probe_md_written": probe_md.exists(),
        "normalized_quote_dir_exists": normalized_quote_dir.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "production_cache_not_mutated": report["production_cache_mutated"] is False,
        "production_provider_config_not_mutated": report["production_provider_config_mutated"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["probe_json"] = str(probe_json)
    report["probe_md"] = str(probe_md)
    report["normalized_quote_dir"] = str(normalized_quote_dir)
    report["source_v2_13_q_report_json"] = str(source_v2_13_q_report_json)
    report["source_v2_13_q_pass_marker"] = str(source_v2_13_q_pass_marker)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_q_report_json": _sha256(source_v2_13_q_report_json),
        "source_v2_13_q_pass_marker": _sha256(source_v2_13_q_pass_marker),
        "probe_json": _sha256(probe_json),
        "probe_md": _sha256(probe_md),
    }
    _write_json(probe_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_finnhub_quote_multi_symbol_live_probe_markdown(report), encoding="utf-8")

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
                f"probe_json={probe_json}",
                f"probe_json_sha256={_sha256(probe_json)}",
                f"probe_md={probe_md}",
                f"probe_md_sha256={_sha256(probe_md)}",
                f"source_v2_13_q_report_json={source_v2_13_q_report_json}",
                f"source_v2_13_q_report_json_sha256={_sha256(source_v2_13_q_report_json)}",
                f"normalized_quote_dir={normalized_quote_dir}",
                f"case_count={report['summary']['case_count']}",
                f"pass_count={report['summary']['pass_count']}",
                f"fail_count={report['summary']['fail_count']}",
                f"blocked_count={report['summary']['blocked_count']}",
                f"probe_symbols={','.join(str(x) for x in report['summary']['probe_symbols'])}",
                f"passed_symbols={','.join(str(x) for x in report['summary']['passed_symbols'])}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
                f"network_used={str(report['network_used']).lower()}",
                "production_records_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
                "env_var_names_only=true",
                "no_secret_values_stored=true",
                "request_urls_not_stored=true",
                "raw_payloads_not_stored=true",
                "suggestion_path_not_enabled=true",
                "social_sentiment_not_enabled=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_live_order_signal=true",
                "no_position_size=true",
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
    parser.add_argument("--run-id", default="v2_13_r_20260712_acceptance")
    parser.add_argument("--source-v2-13-q-report-json", type=Path, default=SOURCE_V2_13_Q_REPORT_JSON)
    parser.add_argument("--source-v2-13-q-pass-marker", type=Path, default=SOURCE_V2_13_Q_PASS_MARKER)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_q_report_json=args.source_v2_13_q_report_json,
        source_v2_13_q_pass_marker=args.source_v2_13_q_pass_marker,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"pass={report['summary']['pass_count']}",
        f"fail={report['summary']['fail_count']}",
        f"blocked={report['summary']['blocked_count']}",
        f"symbols={','.join(str(x) for x in report['summary']['passed_symbols'])}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

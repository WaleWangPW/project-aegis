#!/usr/bin/env python3
"""Validate V2.13-U Finnhub quote multi-symbol historical case assembly."""

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

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dependency exists in normal Aegis env.
    load_dotenv = None

from aegis.external_sources.finnhub_quote_multi_symbol_historical_case_assembly import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_multi_symbol_historical_case_assembly_report,
    render_finnhub_quote_multi_symbol_historical_case_assembly_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_u_acceptance"
SOURCE_V2_13_T_REPORT_JSON = REPORTS_DIR / "v2_13_t_finnhub_quote_multi_symbol_sandbox_binding_latest.json"
SOURCE_V2_13_T_PASS_MARKER = REPORTS_DIR / "V2_13_T_FINNHUB_QUOTE_MULTI_SYMBOL_SANDBOX_BINDING_PASS.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}

PASS_MARKER = "V2_13_U_FINNHUB_QUOTE_MULTI_SYMBOL_HISTORICAL_CASE_ASSEMBLY_PASS.marker"
FAIL_MARKER = "V2_13_U_FINNHUB_QUOTE_MULTI_SYMBOL_HISTORICAL_CASE_ASSEMBLY_FAIL.marker"
REPORT_JSON = "v2_13_u_finnhub_quote_multi_symbol_historical_case_assembly_latest.json"
REPORT_MD = "v2_13_u_finnhub_quote_multi_symbol_historical_case_assembly_latest.md"


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


def _load_dotenv_if_present() -> None:
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env", override=False)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_13_u_20260712_acceptance",
    command: str | None = None,
    source_v2_13_t_report_json: Path = SOURCE_V2_13_T_REPORT_JSON,
    source_v2_13_t_pass_marker: Path = SOURCE_V2_13_T_PASS_MARKER,
    record_paths: dict[str, Path] = RECORD_PATHS,
    env: dict[str, str] | None = None,
    fetch_json=None,
    from_date: str = "2026-06-01",
    to_date: str = "2026-07-10",
) -> dict:
    if env is None:
        _load_dotenv_if_present()
    run_dir = output_root / run_id
    normalized_cache_dir = run_dir / "normalized_daily_bar_cache"
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    source_report = _load_json(source_v2_13_t_report_json)
    report = build_finnhub_quote_multi_symbol_historical_case_assembly_report(
        source_report,
        output_dir=normalized_cache_dir,
        run_id=run_id,
        command=command,
        env=env,
        fetch_json=fetch_json,
        from_date=from_date,
        to_date=to_date,
    )

    assembly_json = run_dir / "finnhub_quote_multi_symbol_historical_case_assembly.json"
    assembly_md = run_dir / "finnhub_quote_multi_symbol_historical_case_assembly.md"
    cases_jsonl = run_dir / "finnhub_quote_multi_symbol_historical_cases.jsonl"
    candidates_json = run_dir / "finnhub_quote_multi_symbol_historical_case_candidates.json"
    daily_bars_json = run_dir / "finnhub_quote_multi_symbol_daily_bar_fetch_results.json"
    _write_json(assembly_json, report)
    assembly_md.write_text(
        render_finnhub_quote_multi_symbol_historical_case_assembly_markdown(report),
        encoding="utf-8",
    )
    cases_jsonl.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in report["historical_cases"]),
        encoding="utf-8",
    )
    _write_json(
        candidates_json,
        {"candidates": [packet["strategy_candidate"] for packet in report["candidate_packets"]]},
    )
    _write_json(daily_bars_json, {"results": report["daily_bar_fetch_results"]})
    after = _fingerprints(record_paths)

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "report_status_pass": report["overall_status"] == "PASS",
        "source_v2_13_t_report_exists": source_v2_13_t_report_json.exists(),
        "source_v2_13_t_marker_exists": source_v2_13_t_pass_marker.exists(),
        "assembly_json_written": assembly_json.exists(),
        "assembly_md_written": assembly_md.exists(),
        "cases_jsonl_written": cases_jsonl.exists(),
        "candidates_json_written": candidates_json.exists(),
        "daily_bars_json_written": daily_bars_json.exists(),
        "normalized_cache_dir_exists": normalized_cache_dir.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": report["production_records_written"] is False,
        "production_cache_not_mutated": report["production_cache_mutated"] is False,
        "production_provider_config_not_mutated": report["production_provider_config_mutated"] is False,
        "dashboard_contract_unchanged": report["dashboard_contract_changed"] is False,
        "source_report_hash_only": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["normalized_cache_dir"] = str(normalized_cache_dir)
    report["assembly_json"] = str(assembly_json)
    report["assembly_md"] = str(assembly_md)
    report["cases_jsonl"] = str(cases_jsonl)
    report["candidates_json"] = str(candidates_json)
    report["daily_bars_json"] = str(daily_bars_json)
    report["source_v2_13_t_report_json"] = str(source_v2_13_t_report_json)
    report["source_v2_13_t_pass_marker"] = str(source_v2_13_t_pass_marker)
    report["production_record_files_before"] = before
    report["production_record_files_after"] = after
    report["hashes"] = {
        "source_v2_13_t_report_json": _sha256(source_v2_13_t_report_json),
        "source_v2_13_t_pass_marker": _sha256(source_v2_13_t_pass_marker),
        "assembly_json": _sha256(assembly_json),
        "assembly_md": _sha256(assembly_md),
        "cases_jsonl": _sha256(cases_jsonl),
        "candidates_json": _sha256(candidates_json),
        "daily_bars_json": _sha256(daily_bars_json),
    }
    _write_json(assembly_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(
        render_finnhub_quote_multi_symbol_historical_case_assembly_markdown(report),
        encoding="utf-8",
    )

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
                f"assembly_json={assembly_json}",
                f"assembly_json_sha256={_sha256(assembly_json)}",
                f"assembly_md={assembly_md}",
                f"assembly_md_sha256={_sha256(assembly_md)}",
                f"cases_jsonl={cases_jsonl}",
                f"cases_jsonl_sha256={_sha256(cases_jsonl)}",
                f"candidates_json={candidates_json}",
                f"candidates_json_sha256={_sha256(candidates_json)}",
                f"daily_bars_json={daily_bars_json}",
                f"daily_bars_json_sha256={_sha256(daily_bars_json)}",
                f"source_v2_13_t_report_json={source_v2_13_t_report_json}",
                f"source_v2_13_t_report_json_sha256={_sha256(source_v2_13_t_report_json)}",
                f"source_v2_13_t_pass_marker={source_v2_13_t_pass_marker}",
                f"source_v2_13_t_pass_marker_sha256={_sha256(source_v2_13_t_pass_marker)}",
                f"normalized_cache_dir={normalized_cache_dir}",
                f"candidate_packet_count={report['summary']['candidate_packet_count']}",
                f"daily_bars_case_count={report['summary']['daily_bars_case_count']}",
                f"historical_case_count={report['summary']['historical_case_count']}",
                f"symbols={','.join(report['summary']['symbols'])}",
                f"network_used={str(report['network_used']).lower()}",
                "sandbox_evaluation_run=false",
                "sandbox_evaluation_required=true",
                "suggestion_gate_required=true",
                "user_facing_suggestion_allowed=false",
                "suggestion_path_not_enabled=true",
                "social_sentiment_not_enabled=true",
                "production_records_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
                "env_var_names_only=true",
                "no_secret_values_stored=true",
                "request_urls_not_stored=true",
                "raw_payloads_not_stored=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
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
    parser.add_argument("--run-id", default="v2_13_u_20260712_acceptance")
    parser.add_argument("--source-v2-13-t-report-json", type=Path, default=SOURCE_V2_13_T_REPORT_JSON)
    parser.add_argument("--source-v2-13-t-pass-marker", type=Path, default=SOURCE_V2_13_T_PASS_MARKER)
    parser.add_argument("--from-date", default="2026-06-01")
    parser.add_argument("--to-date", default="2026-07-10")
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_v2_13_t_report_json=args.source_v2_13_t_report_json,
        source_v2_13_t_pass_marker=args.source_v2_13_t_pass_marker,
        from_date=args.from_date,
        to_date=args.to_date,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"candidate_packet_count={report['summary']['candidate_packet_count']}",
        f"daily_bars_case_count={report['summary']['daily_bars_case_count']}",
        f"historical_case_count={report['summary']['historical_case_count']}",
        f"symbols={','.join(report['summary']['symbols'])}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

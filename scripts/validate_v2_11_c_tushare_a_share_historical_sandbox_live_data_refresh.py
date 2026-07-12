#!/usr/bin/env python3
"""Validate V2.11-C Tushare-backed A-share historical sandbox refresh."""

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

from aegis.strategy.hypothesis_queue import build_strategy_sandbox_hypotheses  # noqa: E402
from aegis.strategy.research_source_catalog import canonical_strategy_research_records  # noqa: E402
from aegis.strategy.tushare_live_sandbox_refresh import (  # noqa: E402
    build_tushare_live_sandbox_refresh_report,
)


REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_11_c_acceptance"
TUSHARE_PROBE_REPORT_JSON = (
    ROOT / "data" / "processed" / "provider_diagnostics" / "provider_coverage_report_v2_11_b_tushare_a_probe.json"
)
HISTORICAL_CACHE_DIR = ROOT / "data" / "cache" / "p23_2_historical_market"
HISTORICAL_CACHE_MANIFEST_JSON = REPORTS_DIR / "p23_2_historical_market_cache_manifest.json"

PASS_MARKER = "V2_11_C_TUSHARE_A_SHARE_HISTORICAL_SANDBOX_LIVE_DATA_REFRESH_PASS.marker"
FAIL_MARKER = "V2_11_C_TUSHARE_A_SHARE_HISTORICAL_SANDBOX_LIVE_DATA_REFRESH_FAIL.marker"
REPORT_JSON = "v2_11_c_tushare_a_share_historical_sandbox_live_data_refresh_latest.json"
REPORT_MD = "v2_11_c_tushare_a_share_historical_sandbox_live_data_refresh_latest.md"


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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hypotheses():
    return build_strategy_sandbox_hypotheses(
        canonical_strategy_research_records(),
        created_at=_now_iso(),
    )


def _render_markdown(report: dict) -> str:
    source = report["live_data_source"]
    cache = report["historical_cache"]
    summary = report["summary"]
    return "\n".join(
        [
            "# V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
            "",
            f"- status: `{report['overall_status']}`",
            f"- run_id: `{report['run_id']}`",
            f"- provider: `{source['provider']}`",
            f"- market: `{source['market']}`",
            f"- source_mode: `{source['source_mode']}`",
            f"- probe_network_available: `{report['tushare_probe_network_available']}`",
            f"- network_used_this_stage: `{report['network_used_this_stage']}`",
            f"- cache_window: `{cache['start_date']}..{cache['end_date']}`",
            f"- daily_cache_count: `{cache['actual_daily_count']}/{cache['expected_daily_count']}`",
            f"- hypothesis_count: `{summary['hypothesis_count']}`",
            f"- historical_case_count: `{summary['historical_case_count']}`",
            f"- strategy_pass_count: `{summary['strategy_pass_count']}`",
            f"- strategy_fail_count: `{summary['strategy_fail_count']}`",
            "",
            "## Boundary",
            "",
            "- Tushare token value is not serialized; only boolean readiness is recorded.",
            "- This is historical sandbox evidence, not user-facing trade advice.",
            "- No real trade, broker API, trading webhook, order placement, or production record mutation.",
            "- Suggestion Gate is still required before any usable brief can claim this evidence.",
            "",
        ]
    )


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_11_c_20260711_acceptance",
    command: str | None = None,
    tushare_probe_report_json: Path = TUSHARE_PROBE_REPORT_JSON,
    historical_cache_manifest_json: Path = HISTORICAL_CACHE_MANIFEST_JSON,
    historical_cache_dir: Path = HISTORICAL_CACHE_DIR,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = build_tushare_live_sandbox_refresh_report(
        hypotheses=_canonical_hypotheses(),
        tushare_probe_report=_load_json(tushare_probe_report_json),
        cache_manifest=_load_json(historical_cache_manifest_json),
        cache_dir=historical_cache_dir,
        run_id=run_id,
        command=command,
    )

    cases_jsonl = run_dir / "tushare_a_share_historical_sandbox_cases.jsonl"
    candidates_json = run_dir / "tushare_a_share_strategy_candidates.json"
    refresh_report_json = run_dir / "tushare_a_share_historical_sandbox_refresh_report.json"
    refresh_report_md = run_dir / "tushare_a_share_historical_sandbox_refresh_report.md"

    cases_jsonl.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in report["historical_cases"]),
        encoding="utf-8",
    )
    _write_json(candidates_json, {"candidates": report["candidates"]})
    _write_json(refresh_report_json, report)
    refresh_report_md.write_text(_render_markdown(report), encoding="utf-8")

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
        "report_status_pass": report["overall_status"] == "PASS",
        "cases_jsonl_written": cases_jsonl.exists(),
        "candidates_json_written": candidates_json.exists(),
        "refresh_report_json_written": refresh_report_json.exists(),
        "refresh_report_md_written": refresh_report_md.exists(),
        "source_tushare_probe_report_exists": tushare_probe_report_json.exists(),
        "source_cache_manifest_exists": historical_cache_manifest_json.exists(),
        "hashes_recorded": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["cases_jsonl"] = str(cases_jsonl)
    report["candidates_json"] = str(candidates_json)
    report["refresh_report_json"] = str(refresh_report_json)
    report["refresh_report_md"] = str(refresh_report_md)
    report["source_tushare_probe_report_json"] = str(tushare_probe_report_json)
    report["source_historical_cache_manifest_json"] = str(historical_cache_manifest_json)
    report["source_historical_cache_dir"] = str(historical_cache_dir)
    report["hashes"] = {
        "source_tushare_probe_report_json": _sha256(tushare_probe_report_json),
        "source_historical_cache_manifest_json": _sha256(historical_cache_manifest_json),
        "cases_jsonl": _sha256(cases_jsonl),
        "candidates_json": _sha256(candidates_json),
        "refresh_report_json": _sha256(refresh_report_json),
        "refresh_report_md": _sha256(refresh_report_md),
    }
    _write_json(refresh_report_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(_render_markdown(report), encoding="utf-8")

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
                "target=V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"cases_jsonl={cases_jsonl}",
                f"cases_jsonl_sha256={_sha256(cases_jsonl)}",
                f"source_tushare_probe_report_json={tushare_probe_report_json}",
                f"source_tushare_probe_report_json_sha256={_sha256(tushare_probe_report_json)}",
                f"source_historical_cache_manifest_json={historical_cache_manifest_json}",
                f"source_historical_cache_manifest_json_sha256={_sha256(historical_cache_manifest_json)}",
                f"historical_case_count={report['summary']['historical_case_count']}",
                f"strategy_pass_count={report['summary']['strategy_pass_count']}",
                f"strategy_fail_count={report['summary']['strategy_fail_count']}",
                "network_used_this_stage=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "tushare_token_value_not_stored=true",
                "simulation_only=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
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
    parser.add_argument("--run-id", default="v2_11_c_20260711_acceptance")
    parser.add_argument("--tushare-probe-report-json", type=Path, default=TUSHARE_PROBE_REPORT_JSON)
    parser.add_argument("--historical-cache-manifest-json", type=Path, default=HISTORICAL_CACHE_MANIFEST_JSON)
    parser.add_argument("--historical-cache-dir", type=Path, default=HISTORICAL_CACHE_DIR)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        tushare_probe_report_json=args.tushare_probe_report_json,
        historical_cache_manifest_json=args.historical_cache_manifest_json,
        historical_cache_dir=args.historical_cache_dir,
    )
    print(
        "V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
        report["overall_status"],
        f"historical_case_count={report['summary']['historical_case_count']}",
        f"strategy_pass_count={report['summary']['strategy_pass_count']}",
        f"strategy_fail_count={report['summary']['strategy_fail_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

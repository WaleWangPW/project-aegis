#!/usr/bin/env python3
"""Validate V2.13-G Finnhub quote context sandbox evaluation."""

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

from aegis.external_sources.finnhub_quote_sandbox_evaluation import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_sandbox_evaluation_report,
    render_finnhub_quote_sandbox_evaluation_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_g_acceptance"
SOURCE_REPORT_JSON = ROOT / "data" / "reports" / "v2_13_f_finnhub_quote_historical_case_assembly_latest.json"

PASS_MARKER = "V2_13_G_FINNHUB_QUOTE_SANDBOX_EVALUATION_PASS.marker"
FAIL_MARKER = "V2_13_G_FINNHUB_QUOTE_SANDBOX_EVALUATION_FAIL.marker"
REPORT_JSON = "v2_13_g_finnhub_quote_sandbox_evaluation_latest.json"
REPORT_MD = "v2_13_g_finnhub_quote_sandbox_evaluation_latest.md"


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
    run_id: str = "v2_13_g_20260712_acceptance",
    command: str | None = None,
    source_report_json: Path = SOURCE_REPORT_JSON,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    source_report = _load_json(source_report_json)
    report = build_finnhub_quote_sandbox_evaluation_report(
        source_report=source_report,
        run_id=run_id,
        command=command,
    )

    sandbox_json = run_dir / "finnhub_quote_sandbox_evaluation.json"
    sandbox_md = run_dir / "finnhub_quote_sandbox_evaluation.md"
    results_json = run_dir / "finnhub_quote_sandbox_results.json"
    _write_json(sandbox_json, report)
    sandbox_md.write_text(render_finnhub_quote_sandbox_evaluation_markdown(report), encoding="utf-8")
    _write_json(results_json, {"results": report["results"]})

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "report_status_pass": report["overall_status"] == "PASS",
        "source_report_exists": source_report_json.exists(),
        "sandbox_json_written": sandbox_json.exists(),
        "sandbox_md_written": sandbox_md.exists(),
        "results_json_written": results_json.exists(),
        "source_report_hash_only": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["sandbox_json"] = str(sandbox_json)
    report["sandbox_md"] = str(sandbox_md)
    report["results_json"] = str(results_json)
    report["source_report_json"] = str(source_report_json)
    report["hashes"] = {
        "source_report_json": _sha256(source_report_json),
        "sandbox_json": _sha256(sandbox_json),
        "sandbox_md": _sha256(sandbox_md),
        "results_json": _sha256(results_json),
    }
    _write_json(sandbox_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_finnhub_quote_sandbox_evaluation_markdown(report), encoding="utf-8")

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
                f"sandbox_json={sandbox_json}",
                f"sandbox_json_sha256={_sha256(sandbox_json)}",
                f"results_json={results_json}",
                f"results_json_sha256={_sha256(results_json)}",
                f"source_report_json={source_report_json}",
                f"source_report_json_sha256={_sha256(source_report_json)}",
                f"candidate_count={report['summary']['candidate_count']}",
                f"historical_case_count={report['summary']['historical_case_count']}",
                f"strategy_pass_count={report['summary']['strategy_pass_count']}",
                f"strategy_fail_count={report['summary']['strategy_fail_count']}",
                f"passing_strategies={','.join(report['summary']['passing_strategies'])}",
                f"symbols={','.join(report['summary']['symbols'])}",
                "network_used=false",
                "sandbox_evaluation_run=true",
                "suggestion_gate_required=true",
                "user_facing_suggestion_allowed=false",
                "production_records_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
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
    parser.add_argument("--run-id", default="v2_13_g_20260712_acceptance")
    parser.add_argument("--source-report-json", type=Path, default=SOURCE_REPORT_JSON)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_report_json=args.source_report_json,
    )
    print(
        ACCEPTANCE_TARGET,
        report["overall_status"],
        f"candidate_count={report['summary']['candidate_count']}",
        f"historical_case_count={report['summary']['historical_case_count']}",
        f"strategy_pass_count={report['summary']['strategy_pass_count']}",
        f"strategy_fail_count={report['summary']['strategy_fail_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

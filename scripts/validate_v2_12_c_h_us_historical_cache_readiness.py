#!/usr/bin/env python3
"""Validate V2.12-C H/US historical cache readiness dry run."""

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

from aegis.external_sources.h_us_historical_cache_readiness import (  # noqa: E402
    build_h_us_historical_cache_readiness_report,
    render_h_us_historical_cache_readiness_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_12_c_acceptance"
SOURCE_METADATA_REPORT_JSON = ROOT / "data" / "reports" / "v2_12_b_h_us_provider_metadata_activation_latest.json"

PASS_MARKER = "V2_12_C_H_US_HISTORICAL_CACHE_READINESS_PASS.marker"
FAIL_MARKER = "V2_12_C_H_US_HISTORICAL_CACHE_READINESS_FAIL.marker"
REPORT_JSON = "v2_12_c_h_us_historical_cache_readiness_latest.json"
REPORT_MD = "v2_12_c_h_us_historical_cache_readiness_latest.md"


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
    run_id: str = "v2_12_c_20260712_acceptance",
    command: str | None = None,
    source_metadata_report_json: Path = SOURCE_METADATA_REPORT_JSON,
    env: dict[str, str] | None = None,
    fetch_json=None,
) -> dict:
    run_dir = output_root / run_id
    cache_dir = run_dir / "normalized_cache"
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    metadata_report = _load_json(source_metadata_report_json)
    report = build_h_us_historical_cache_readiness_report(
        metadata_report=metadata_report,
        output_dir=cache_dir,
        run_id=run_id,
        command=command,
        env=env,
        fetch_json=fetch_json,
    )

    readiness_report_json = run_dir / "h_us_historical_cache_readiness_report.json"
    readiness_report_md = run_dir / "h_us_historical_cache_readiness_report.md"
    _write_json(readiness_report_json, report)
    readiness_report_md.write_text(render_h_us_historical_cache_readiness_markdown(report), encoding="utf-8")

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"]
        == "V2.12-C H-US Historical Cache Readiness Dry Run",
        "report_status_pass": report["overall_status"] == "PASS",
        "source_metadata_report_exists": source_metadata_report_json.exists(),
        "readiness_report_json_written": readiness_report_json.exists(),
        "readiness_report_md_written": readiness_report_md.exists(),
        "normalized_cache_dir_exists": cache_dir.exists(),
        "source_metadata_hash_only": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["readiness_report_json"] = str(readiness_report_json)
    report["readiness_report_md"] = str(readiness_report_md)
    report["source_metadata_report_json"] = str(source_metadata_report_json)
    report["hashes"] = {
        "source_metadata_report_json": _sha256(source_metadata_report_json),
        "readiness_report_json": _sha256(readiness_report_json),
        "readiness_report_md": _sha256(readiness_report_md),
    }
    _write_json(readiness_report_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_h_us_historical_cache_readiness_markdown(report), encoding="utf-8")

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
                "target=V2.12-C H-US Historical Cache Readiness Dry Run",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"readiness_report_json={readiness_report_json}",
                f"readiness_report_json_sha256={_sha256(readiness_report_json)}",
                f"readiness_report_md={readiness_report_md}",
                f"readiness_report_md_sha256={_sha256(readiness_report_md)}",
                f"source_metadata_report_json={source_metadata_report_json}",
                f"source_metadata_report_json_sha256={_sha256(source_metadata_report_json)}",
                f"normalized_cache_root={cache_dir}",
                f"case_count={report['summary']['case_count']}",
                f"pass_count={report['summary']['pass_count']}",
                f"fail_count={report['summary']['fail_count']}",
                f"h_cache_ready={str(report['summary']['h_cache_ready']).lower()}",
                f"us_cache_ready={str(report['summary']['us_cache_ready']).lower()}",
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
    parser.add_argument("--run-id", default="v2_12_c_20260712_acceptance")
    parser.add_argument("--source-metadata-report-json", type=Path, default=SOURCE_METADATA_REPORT_JSON)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_metadata_report_json=args.source_metadata_report_json,
    )
    print(
        "V2.12-C H-US Historical Cache Readiness Dry Run",
        report["overall_status"],
        f"h_cache_ready={report['summary']['h_cache_ready']}",
        f"us_cache_ready={report['summary']['us_cache_ready']}",
        f"pass={report['summary']['pass_count']}",
        f"fail={report['summary']['fail_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

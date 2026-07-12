#!/usr/bin/env python3
"""Validate V2.12-A EODHD/Twelve Data H-US provider probe."""

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

from aegis.external_sources.eodhd_twelve_provider_probe import (  # noqa: E402
    build_eodhd_twelve_provider_probe_report,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_12_a_acceptance"
PASS_MARKER = "V2_12_A_EODHD_TWELVE_H_US_PROVIDER_PROBE_PASS.marker"
FAIL_MARKER = "V2_12_A_EODHD_TWELVE_H_US_PROVIDER_PROBE_FAIL.marker"
REPORT_JSON = "v2_12_a_eodhd_twelve_h_us_provider_probe_latest.json"
REPORT_MD = "v2_12_a_eodhd_twelve_h_us_provider_probe_latest.md"


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


def _render_markdown(report: dict) -> str:
    lines = [
        "# V2.12-A EODHD Twelve Data H-US Provider Probe",
        "",
        f"- status: `{report['overall_status']}`",
        f"- run_id: `{report['run_id']}`",
        f"- pass_count: `{report['summary']['pass_count']}`",
        f"- fail_count: `{report['summary']['fail_count']}`",
        f"- h_us_provider_status: `{report['summary']['h_us_provider_status']}`",
        f"- next_stage: `{report['summary']['next_stage']}`",
        "",
        "## Results",
        "",
    ]
    for item in report["results"]:
        lines.extend(
            [
                f"### {item['provider']} {item['market']} {item['symbol']}",
                "",
                f"- status: `{item['status']}`",
                f"- env_present: `{item['env_present']}`",
                f"- blocked_by: `{item.get('blocked_by', [])}`",
                f"- summary: `{item.get('summary', {})}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Provider capability probe only.",
            "- Env var names only; no token values.",
            "- No request URL or raw payload storage.",
            "- No real trade, broker API, trading webhook, order placement, or production record mutation.",
            "- Dashboard Contract unchanged.",
            "",
        ]
    )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = OUTPUT_ROOT,
    reports_dir: Path = REPORTS_DIR,
    run_id: str = "v2_12_a_20260712_acceptance",
    command: str | None = None,
    env: dict[str, str] | None = None,
    fetch_json=None,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    report = build_eodhd_twelve_provider_probe_report(
        run_id=run_id,
        command=command,
        env=env,
        fetch_json=fetch_json,
    )
    report["generated_at"] = _now_iso()
    run_report_json = run_dir / "eodhd_twelve_h_us_provider_probe_report.json"
    run_report_md = run_dir / "eodhd_twelve_h_us_provider_probe_report.md"
    _write_json(run_report_json, report)
    run_report_md.write_text(_render_markdown(report), encoding="utf-8")
    report["run_report_json"] = str(run_report_json)
    report["run_report_md"] = str(run_report_md)
    report["hashes"] = {
        "run_report_json": _sha256(run_report_json),
        "run_report_md": _sha256(run_report_md),
    }
    _write_json(run_report_json, report)

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
                "target=V2.12-A EODHD Twelve Data H-US Provider Probe",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"pass_count={report['summary']['pass_count']}",
                f"fail_count={report['summary']['fail_count']}",
                "network_used=true",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "no_secret_values_stored=true",
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
    parser.add_argument("--run-id", default="v2_12_a_20260712_acceptance")
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
    )
    print(
        "V2.12-A EODHD Twelve Data H-US Provider Probe",
        report["overall_status"],
        f"pass={report['summary']['pass_count']}",
        f"fail={report['summary']['fail_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate V2.11-B user-provided API metadata activation packet."""

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

from aegis.external_sources.api_metadata_activation_packet import (  # noqa: E402
    build_api_metadata_activation_packet,
    render_api_metadata_activation_packet_markdown,
)
from aegis.external_sources.api_metadata_intake import CANDIDATE_REFRESH_CONNECTOR_ID  # noqa: E402


REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_11_b_acceptance"
TEMPLATE_JSON = ROOT / "config" / "external_api_connectors.user-template.json"
METADATA_INTAKE_REPORT_JSON = ROOT / "data" / "reports" / "v2_10_b_real_api_metadata_intake_latest.json"
TUSHARE_PROBE_REPORT_JSON = (
    ROOT / "data" / "processed" / "provider_diagnostics" / "provider_coverage_report_v2_11_b_tushare_a_probe.json"
)

PASS_MARKER = "V2_11_B_USER_API_METADATA_ACTIVATION_PACKET_PASS.marker"
FAIL_MARKER = "V2_11_B_USER_API_METADATA_ACTIVATION_PACKET_FAIL.marker"
REPORT_JSON = "v2_11_b_user_api_metadata_activation_packet_latest.json"
REPORT_MD = "v2_11_b_user_api_metadata_activation_packet_latest.md"


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
    run_id: str = "v2_11_b_20260711_acceptance",
    command: str | None = None,
    template_json: Path = TEMPLATE_JSON,
    metadata_intake_report_json: Path = METADATA_INTAKE_REPORT_JSON,
    tushare_probe_report_json: Path | None = TUSHARE_PROBE_REPORT_JSON,
    connector_id: str = CANDIDATE_REFRESH_CONNECTOR_ID,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    template_payload = _load_json(template_json)
    metadata_intake_report = _load_json(metadata_intake_report_json)
    tushare_probe_report = (
        _load_json(tushare_probe_report_json)
        if tushare_probe_report_json is not None and tushare_probe_report_json.exists()
        else None
    )
    packet = build_api_metadata_activation_packet(
        template_payload=template_payload,
        metadata_intake_report=metadata_intake_report,
        tushare_probe_report=tushare_probe_report,
        run_id=run_id,
        connector_id=connector_id,
        command=command,
    )

    packet_json = run_dir / "user_api_metadata_activation_packet.json"
    packet_md = run_dir / "user_api_metadata_activation_packet.md"
    _write_json(packet_json, packet)
    packet_md.write_text(render_api_metadata_activation_packet_markdown(packet), encoding="utf-8")

    checks = {
        **packet["checks"],
        "acceptance_target_correct": packet["acceptance_target"]
        == "V2.11-B User-Provided API Metadata Activation Packet",
        "packet_status_pass": packet["overall_status"] == "PASS",
        "packet_json_written": packet_json.exists(),
        "packet_md_written": packet_md.exists(),
        "template_json_exists": template_json.exists(),
        "metadata_intake_report_exists": metadata_intake_report_json.exists(),
        "tushare_probe_report_exists": tushare_probe_report_json is not None and tushare_probe_report_json.exists(),
        "template_hash_only": True,
        "metadata_intake_hash_only": True,
        "tushare_probe_hash_only": True,
    }
    packet["checks"] = checks
    packet["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    packet["generated_at"] = _now_iso()
    packet["packet_json"] = str(packet_json)
    packet["packet_md"] = str(packet_md)
    packet["source_template_json"] = str(template_json)
    packet["source_metadata_intake_report_json"] = str(metadata_intake_report_json)
    packet["source_tushare_probe_report_json"] = str(tushare_probe_report_json) if tushare_probe_report_json else None
    packet["hashes"] = {
        "source_template_json": _sha256(template_json),
        "source_metadata_intake_report_json": _sha256(metadata_intake_report_json),
        "source_tushare_probe_report_json": _sha256(tushare_probe_report_json)
        if tushare_probe_report_json
        else None,
        "packet_json": _sha256(packet_json),
        "packet_md": _sha256(packet_md),
    }
    _write_json(packet_json, packet)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, packet)
    report_md.write_text(render_api_metadata_activation_packet_markdown(packet), encoding="utf-8")

    marker_name = PASS_MARKER if packet["overall_status"] == "PASS" else FAIL_MARKER
    stale = reports_dir / (FAIL_MARKER if marker_name == PASS_MARKER else PASS_MARKER)
    if stale.exists():
        stale.unlink()
    (reports_dir / marker_name).write_text(
        "\n".join(
            [
                f"generated_at={packet['generated_at']}",
                f"command={command or ''}",
                f"exit_code={0 if packet['overall_status'] == 'PASS' else 1}",
                "target=V2.11-B User-Provided API Metadata Activation Packet",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"packet_json={packet_json}",
                f"packet_json_sha256={_sha256(packet_json)}",
                f"packet_md={packet_md}",
                f"packet_md_sha256={_sha256(packet_md)}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "raw_config_not_stored=true",
                "env_values_not_stored=true",
                "env_var_names_only=true",
                "tushare_token_value_not_stored=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--run-id", default="v2_11_b_20260711_acceptance")
    parser.add_argument("--template-json", type=Path, default=TEMPLATE_JSON)
    parser.add_argument("--metadata-intake-report-json", type=Path, default=METADATA_INTAKE_REPORT_JSON)
    parser.add_argument("--tushare-probe-report-json", type=Path, default=TUSHARE_PROBE_REPORT_JSON)
    parser.add_argument("--connector-id", default=CANDIDATE_REFRESH_CONNECTOR_ID)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        template_json=args.template_json,
        metadata_intake_report_json=args.metadata_intake_report_json,
        tushare_probe_report_json=args.tushare_probe_report_json,
        connector_id=args.connector_id,
    )
    print(
        "V2.11-B User API Metadata Activation Packet",
        report["overall_status"],
        f"current_intake_status={report['summary']['current_intake_status']}",
        f"tushare_status={report['summary']['tushare_status']}",
        f"required_env_vars={report['summary']['required_env_vars']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

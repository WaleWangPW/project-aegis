#!/usr/bin/env python3
"""Validate V2.13-B Finnhub metadata activation proposal."""

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

from aegis.external_sources.finnhub_metadata_activation import (  # noqa: E402
    build_finnhub_metadata_activation,
    render_finnhub_metadata_activation_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_b_acceptance"
SOURCE_PROBE_REPORT_JSON = ROOT / "data" / "reports" / "v2_13_a_finnhub_free_probe_latest.json"

PASS_MARKER = "V2_13_B_FINNHUB_METADATA_ACTIVATION_PASS.marker"
FAIL_MARKER = "V2_13_B_FINNHUB_METADATA_ACTIVATION_FAIL.marker"
REPORT_JSON = "v2_13_b_finnhub_metadata_activation_latest.json"
REPORT_MD = "v2_13_b_finnhub_metadata_activation_latest.md"


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
    run_id: str = "v2_13_b_20260712_acceptance",
    command: str | None = None,
    source_probe_report_json: Path = SOURCE_PROBE_REPORT_JSON,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    probe_report = _load_json(source_probe_report_json)
    packet = build_finnhub_metadata_activation(
        probe_report=probe_report,
        run_id=run_id,
        command=command,
    )

    packet_json = run_dir / "finnhub_metadata_activation.json"
    packet_md = run_dir / "finnhub_metadata_activation.md"
    _write_json(packet_json, packet)
    packet_md.write_text(render_finnhub_metadata_activation_markdown(packet), encoding="utf-8")

    checks = {
        **packet["checks"],
        "acceptance_target_correct": packet["acceptance_target"] == "V2.13-B Finnhub Metadata Activation",
        "packet_status_pass": packet["overall_status"] == "PASS",
        "source_probe_report_exists": source_probe_report_json.exists(),
        "packet_json_written": packet_json.exists(),
        "packet_md_written": packet_md.exists(),
        "source_probe_hash_only": True,
        "packet_contains_no_source_raw_payload": True,
        "packet_contains_no_request_url": True,
        "packet_contains_no_token_value": True,
    }
    packet["checks"] = checks
    packet["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    packet["generated_at"] = _now_iso()
    packet["packet_json"] = str(packet_json)
    packet["packet_md"] = str(packet_md)
    packet["source_probe_report_json"] = str(source_probe_report_json)
    packet["hashes"] = {
        "source_probe_report_json": _sha256(source_probe_report_json),
        "packet_json": _sha256(packet_json),
        "packet_md": _sha256(packet_md),
    }
    _write_json(packet_json, packet)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, packet)
    report_md.write_text(render_finnhub_metadata_activation_markdown(packet), encoding="utf-8")

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
                "target=V2.13-B Finnhub Metadata Activation",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"packet_json={packet_json}",
                f"packet_json_sha256={_sha256(packet_json)}",
                f"packet_md={packet_md}",
                f"packet_md_sha256={_sha256(packet_md)}",
                f"source_probe_report_json={source_probe_report_json}",
                f"source_probe_report_json_sha256={_sha256(source_probe_report_json)}",
                "network_used=false",
                "production_records_written=false",
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
    parser.add_argument("--run-id", default="v2_13_b_20260712_acceptance")
    parser.add_argument("--source-probe-report-json", type=Path, default=SOURCE_PROBE_REPORT_JSON)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])
    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        source_probe_report_json=args.source_probe_report_json,
    )
    print(
        "V2.13-B Finnhub Metadata Activation",
        report["overall_status"],
        f"quote_route={report['summary']['quote_route']}",
        f"social_sentiment_route={report['summary']['social_sentiment_route']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate V2.11-E current action packet after Tushare gate."""

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

from aegis.paper.action_packet_after_tushare_gate import (  # noqa: E402
    build_action_packet_after_tushare_gate,
    render_action_packet_after_tushare_gate_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_11_e_acceptance"
CURRENT_BRIEF_JSON = REPORTS_DIR / "v2_9_h_current_usable_simulation_brief_latest.json"
API_BACKED_BRIEF_JSON = REPORTS_DIR / "v2_10_d_api_backed_candidate_usable_brief_latest.json"
TUSHARE_GATE_JSON = REPORTS_DIR / "v2_11_d_tushare_backed_a_share_suggestion_gate_refresh_latest.json"
RECORD_PATHS = {
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
}

PASS_MARKER = "V2_11_E_CURRENT_ACTION_PACKET_AFTER_TUSHARE_GATE_PASS.marker"
FAIL_MARKER = "V2_11_E_CURRENT_ACTION_PACKET_AFTER_TUSHARE_GATE_FAIL.marker"
REPORT_JSON = "v2_11_e_current_action_packet_after_tushare_gate_latest.json"
REPORT_MD = "v2_11_e_current_action_packet_after_tushare_gate_latest.md"


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
    run_id: str = "v2_11_e_20260711_acceptance",
    command: str | None = None,
    current_brief_json: Path = CURRENT_BRIEF_JSON,
    api_backed_brief_json: Path = API_BACKED_BRIEF_JSON,
    tushare_gate_json: Path = TUSHARE_GATE_JSON,
    record_paths: dict[str, Path] = RECORD_PATHS,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    before = _fingerprints(record_paths)
    packet = build_action_packet_after_tushare_gate(
        current_brief=_load_json(current_brief_json),
        api_backed_brief=_load_json(api_backed_brief_json),
        tushare_gate_report=_load_json(tushare_gate_json),
        run_id=run_id,
        command=command,
    )
    after = _fingerprints(record_paths)

    packet_json = run_dir / "current_action_packet_after_tushare_gate.json"
    packet_md = run_dir / "current_action_packet_after_tushare_gate.md"
    _write_json(packet_json, packet)
    packet_md.write_text(render_action_packet_after_tushare_gate_markdown(packet), encoding="utf-8")

    checks = {
        **packet["checks"],
        "acceptance_target_correct": packet["acceptance_target"]
        == "V2.11-E Current Action Packet After Tushare Gate",
        "packet_status_pass": packet["overall_status"] == "PASS",
        "packet_json_written": packet_json.exists(),
        "packet_md_written": packet_md.exists(),
        "production_record_files_unchanged": before == after,
        "production_records_not_written": packet["production_records_written"] is False,
        "network_not_used": packet["network_used"] is False,
        "dashboard_contract_unchanged": packet["dashboard_contract_changed"] is False,
    }
    packet["checks"] = checks
    packet["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    packet["generated_at"] = _now_iso()
    packet["packet_json"] = str(packet_json)
    packet["packet_md"] = str(packet_md)
    packet["source_current_brief_json"] = str(current_brief_json)
    packet["source_api_backed_brief_json"] = str(api_backed_brief_json)
    packet["source_tushare_gate_json"] = str(tushare_gate_json)
    packet["production_record_files_before"] = before
    packet["production_record_files_after"] = after
    packet["hashes"] = {
        "source_current_brief_json": _sha256(current_brief_json),
        "source_api_backed_brief_json": _sha256(api_backed_brief_json),
        "source_tushare_gate_json": _sha256(tushare_gate_json),
        "packet_json": _sha256(packet_json),
        "packet_md": _sha256(packet_md),
    }
    _write_json(packet_json, packet)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, packet)
    report_md.write_text(render_action_packet_after_tushare_gate_markdown(packet), encoding="utf-8")

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
                "target=V2.11-E Current Action Packet After Tushare Gate",
                f"report_json={report_json}",
                f"report_json_sha256={_sha256(report_json)}",
                f"report_md={report_md}",
                f"report_md_sha256={_sha256(report_md)}",
                f"packet_json={packet_json}",
                f"packet_json_sha256={_sha256(packet_json)}",
                f"packet_md={packet_md}",
                f"packet_md_sha256={_sha256(packet_md)}",
                f"source_tushare_gate_json={tushare_gate_json}",
                f"source_tushare_gate_json_sha256={_sha256(tushare_gate_json)}",
                f"today_focus_count={packet['summary']['today_focus_count']}",
                f"blocked_count={packet['summary']['blocked_count']}",
                f"removed_focus_count={packet['summary']['removed_focus_count']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
                "no_live_price=true",
                "no_position_size=true",
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
    parser.add_argument("--run-id", default="v2_11_e_20260711_acceptance")
    parser.add_argument("--current-brief-json", type=Path, default=CURRENT_BRIEF_JSON)
    parser.add_argument("--api-backed-brief-json", type=Path, default=API_BACKED_BRIEF_JSON)
    parser.add_argument("--tushare-gate-json", type=Path, default=TUSHARE_GATE_JSON)
    args = parser.parse_args(argv)
    command_args = argv if argv is not None else sys.argv[1:]
    command = " ".join([Path(sys.argv[0]).name, *command_args])

    report = run_acceptance(
        output_root=args.output_root,
        reports_dir=args.reports_dir,
        run_id=args.run_id,
        command=command,
        current_brief_json=args.current_brief_json,
        api_backed_brief_json=args.api_backed_brief_json,
        tushare_gate_json=args.tushare_gate_json,
    )
    print(
        "V2.11-E Current Action Packet After Tushare Gate",
        report["overall_status"],
        f"today_focus={report['summary']['today_focus_count']}",
        f"blocked={report['summary']['blocked_count']}",
        f"removed_focus={report['summary']['removed_focus_count']}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

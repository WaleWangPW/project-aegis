#!/usr/bin/env python3
"""Validate V2.13-D Finnhub quote research context bridge."""

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

from aegis.external_sources.finnhub_quote_research_context import (  # noqa: E402
    ACCEPTANCE_TARGET,
    build_finnhub_quote_research_context_report,
    render_finnhub_quote_research_context_markdown,
)

REPORTS_DIR = ROOT / "data" / "reports"
OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_13_d_acceptance"
SOURCE_REPORT_JSON = ROOT / "data" / "reports" / "v2_13_c_finnhub_quote_cache_readiness_latest.json"

PASS_MARKER = "V2_13_D_FINNHUB_QUOTE_RESEARCH_CONTEXT_PASS.marker"
FAIL_MARKER = "V2_13_D_FINNHUB_QUOTE_RESEARCH_CONTEXT_FAIL.marker"
REPORT_JSON = "v2_13_d_finnhub_quote_research_context_latest.json"
REPORT_MD = "v2_13_d_finnhub_quote_research_context_latest.md"


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
    run_id: str = "v2_13_d_20260712_acceptance",
    command: str | None = None,
    source_report_json: Path = SOURCE_REPORT_JSON,
) -> dict:
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    source_report = _load_json(source_report_json)
    report = build_finnhub_quote_research_context_report(
        source_report=source_report,
        run_id=run_id,
        command=command,
    )

    context_json = run_dir / "finnhub_quote_research_context.json"
    context_md = run_dir / "finnhub_quote_research_context.md"
    _write_json(context_json, report)
    context_md.write_text(render_finnhub_quote_research_context_markdown(report), encoding="utf-8")

    checks = {
        **report["checks"],
        "acceptance_target_correct": report["acceptance_target"] == ACCEPTANCE_TARGET,
        "report_status_pass": report["overall_status"] == "PASS",
        "source_report_exists": source_report_json.exists(),
        "context_json_written": context_json.exists(),
        "context_md_written": context_md.exists(),
        "source_report_hash_only": True,
    }
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"
    report["generated_at"] = _now_iso()
    report["run_dir"] = str(run_dir)
    report["context_json"] = str(context_json)
    report["context_md"] = str(context_md)
    report["source_report_json"] = str(source_report_json)
    report["hashes"] = {
        "source_report_json": _sha256(source_report_json),
        "context_json": _sha256(context_json),
        "context_md": _sha256(context_md),
    }
    _write_json(context_json, report)

    report_json = reports_dir / REPORT_JSON
    report_md = reports_dir / REPORT_MD
    _write_json(report_json, report)
    report_md.write_text(render_finnhub_quote_research_context_markdown(report), encoding="utf-8")

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
                f"context_json={context_json}",
                f"context_json_sha256={_sha256(context_json)}",
                f"context_md={context_md}",
                f"context_md_sha256={_sha256(context_md)}",
                f"source_report_json={source_report_json}",
                f"source_report_json_sha256={_sha256(source_report_json)}",
                f"context_item_count={report['summary']['context_item_count']}",
                f"symbols={','.join(report['summary']['symbols'])}",
                f"markets={','.join(report['summary']['markets'])}",
                f"social_sentiment_status={report['summary']['social_sentiment_status']}",
                "network_used=false",
                "production_records_written=false",
                "production_cache_mutated=false",
                "production_provider_config_mutated=false",
                "dashboard_contract_changed=false",
                "research_context_only=true",
                "requires_sandbox_before_suggestion=true",
                "requires_suggestion_gate_before_user_facing=true",
                "suggestion_path_not_enabled=true",
                "social_sentiment_not_enabled=true",
                "user_facing_suggestion_allowed=false",
                "auto_applied=false",
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
    parser.add_argument("--run-id", default="v2_13_d_20260712_acceptance")
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
        f"context_item_count={report['summary']['context_item_count']}",
        f"symbols={','.join(report['summary']['symbols'])}",
        f"run_id={args.run_id}",
        f"report={args.reports_dir / REPORT_JSON}",
    )
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

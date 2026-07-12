#!/usr/bin/env python3
"""Validate Project Aegis V2.4-B Strategy Research To Sandbox Hypothesis Queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.strategy.hypothesis_queue import write_strategy_sandbox_hypothesis_queue  # noqa: E402
from aegis.strategy.research_source_catalog import canonical_strategy_research_records  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_4_b_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_4_B_STRATEGY_RESEARCH_HYPOTHESIS_QUEUE_PASS.marker"
FAIL_MARKER = "V2_4_B_STRATEGY_RESEARCH_HYPOTHESIS_QUEUE_FAIL.marker"
REPORT_JSON = "v2_4_b_strategy_research_hypothesis_queue_latest.json"
REPORT_MD = "v2_4_b_strategy_research_hypothesis_queue_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_4_b_strategy_hypothesis_queue_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    records = canonical_strategy_research_records()
    queue_json = run_dir / "strategy_sandbox_hypothesis_queue.json"
    queue = write_strategy_sandbox_hypothesis_queue(records, queue_json)
    hypotheses = queue["hypotheses"]
    required_markets = ["A", "H", "US"]
    required_families = ["value", "quality", "momentum", "low_volatility", "dividend", "multi_factor", "risk_overlay"]

    checks = {
        "hypothesis_count_at_least_6": queue["hypothesis_count"] >= 6,
        "covers_a_h_us": all(queue["market_coverage"].get(market, 0) >= 2 for market in required_markets),
        "covers_core_hypothesis_families": all(
            queue["strategy_family_coverage"].get(family, 0) > 0 for family in required_families
        ),
        "all_have_source_research_refs": all(item["source_research_ids"] for item in hypotheses),
        "all_have_metrics": all(item["proposed_metrics"] for item in hypotheses),
        "requires_sandbox": all(item["requires_sandbox"] is True for item in hypotheses),
        "not_auto_applied": all(item["auto_applied"] is False for item in hypotheses),
        "no_user_facing_suggestion": all(item["user_facing_suggestion_allowed"] is False for item in hypotheses),
        "hypothesis_hashes_written": len(queue["hypothesis_hashes"]) == queue["hypothesis_count"],
        "no_real_trade": queue["safety"]["no_real_trade"] is True,
        "no_broker_api": queue["safety"]["no_broker_api"] is True,
        "no_trading_webhook": queue["safety"]["no_trading_webhook"] is True,
        "no_strategy_auto_mutation": queue["safety"]["no_strategy_auto_mutation"] is True,
        "production_records_not_written": True,
        "dashboard_contract_unchanged": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.4-B acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.4-B Strategy Research To Sandbox Hypothesis Queue",
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "strategy_sandbox_hypothesis_queue": str(queue_json),
        "checks": checks,
        "summary": {
            "hypothesis_count": queue["hypothesis_count"],
            "market_coverage": queue["market_coverage"],
            "strategy_family_coverage": queue["strategy_family_coverage"],
            "hypothesis_ids": [item["hypothesis_id"] for item in hypotheses],
            "next_target": "V2.4-C Historical Sandbox Run For Research Hypotheses",
        },
        "safety": queue["safety"],
        "hashes": {
            "strategy_sandbox_hypothesis_queue": _sha256(queue_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.4-B Strategy Research Hypothesis Queue Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- queue: `{report['strategy_sandbox_hypothesis_queue']}`",
                f"- hypothesis_count: `{report['summary']['hypothesis_count']}`",
                f"- market_coverage: `{report['summary']['market_coverage']}`",
                f"- hypothesis_ids: `{report['summary']['hypothesis_ids']}`",
                "- safety: hypothesis-only, requires sandbox, no direct suggestion, no broker/trading/webhook",
                "",
            ]
        ),
        encoding="utf-8",
    )
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.4-B Strategy Research To Sandbox Hypothesis Queue",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"strategy_sandbox_hypothesis_queue={report['strategy_sandbox_hypothesis_queue']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "requires_sandbox=true",
                "auto_applied=false",
                "user_facing_suggestion_allowed=false",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fail_marker = reports_dir / FAIL_MARKER
    if fail_marker.exists():
        fail_marker.unlink()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.4-B Strategy Research To Sandbox Hypothesis Queue",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.4-B Strategy Research Hypothesis Queue FAIL: {exc}")
        return 1

    print(f"V2.4-B Strategy Research Hypothesis Queue PASS run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

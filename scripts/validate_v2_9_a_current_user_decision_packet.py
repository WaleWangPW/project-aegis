#!/usr/bin/env python3
"""Validate Project Aegis V2.9-A Current User Decision Packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_9_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"
DEFAULT_CONCRETE_BRIEF_JSON = (
    ROOT
    / "data"
    / "processed"
    / "v2_8_h_acceptance"
    / "v2_8_h_20260711_acceptance"
    / "concrete_candidate_usable_brief.json"
)
DEFAULT_SANDBOX_REPORT_JSON = ROOT / "data" / "reports" / "v2_8_d_refresh_queue_historical_sandbox_latest.json"
DEFAULT_API_DRY_RUN_JSON = ROOT / "data" / "reports" / "v2_8_j_real_user_api_candidate_refresh_dry_run_latest.json"

PASS_MARKER = "V2_9_A_CURRENT_USER_DECISION_PACKET_PASS.marker"
FAIL_MARKER = "V2_9_A_CURRENT_USER_DECISION_PACKET_FAIL.marker"
REPORT_JSON = "v2_9_a_current_user_decision_packet_latest.json"
REPORT_MD = "v2_9_a_current_user_decision_packet_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_9_a_current_user_decision_packet_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_plain_action(item: Mapping) -> str:
    return (
        "加入模拟观察清单；先人工核对实时行情、公司事件、持仓冲突和个人风险预算，"
        "如要交易只能在 Aegis 外部软件手动执行，并把截图或文字结果回传。"
    )


def _blocked_plain_action(item: Mapping) -> str:
    reasons = ", ".join(item.get("blocked_by") or ["blocked"])
    return f"不要用于模拟入场；先解决阻断原因：{reasons}。"


def _build_packet(
    *,
    concrete_brief: Mapping,
    sandbox_report: Mapping,
    api_dry_run_report: Mapping,
    run_id: str,
    generated_at: str | None = None,
) -> dict:
    items = list(concrete_brief.get("items", []))
    candidates = [item for item in items if item.get("brief_status") == "candidate"]
    blocked = [item for item in items if item.get("brief_status") == "blocked"]
    packet_items = []
    for item in candidates:
        packet_items.append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "market": item.get("market"),
                "strategy_id": item.get("strategy_id"),
                "candidate_score": item.get("candidate_score"),
                "candidate_status": item.get("candidate_status"),
                "source_mode": concrete_brief.get("source_mode"),
                "decision_packet_status": "simulation_candidate",
                "user_action": _candidate_plain_action(item),
                "why": item.get("reasons", [])[:5],
                "risk_warnings": item.get("risk_warnings", [])[:8],
                "blocked_by": [],
                "evidence_refs": item.get("evidence_refs", [])[:10],
            }
        )
    for item in blocked:
        packet_items.append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "market": item.get("market"),
                "strategy_id": item.get("strategy_id"),
                "candidate_score": item.get("candidate_score"),
                "candidate_status": item.get("candidate_status"),
                "source_mode": concrete_brief.get("source_mode"),
                "decision_packet_status": "blocked",
                "user_action": _blocked_plain_action(item),
                "why": item.get("reasons", [])[:5],
                "risk_warnings": item.get("risk_warnings", [])[:8],
                "blocked_by": item.get("blocked_by", []),
                "evidence_refs": item.get("evidence_refs", [])[:10],
            }
        )

    sandbox_summary = sandbox_report.get("summary", {})
    api_summary = api_dry_run_report.get("summary", {})
    candidate_markets = sorted({item.get("market") for item in candidates if item.get("market")})
    blocked_markets = sorted({item.get("market") for item in blocked if item.get("market")})
    checks = {
        "has_a_h_us_candidates": {"A", "H", "US"}.issubset(candidate_markets),
        "has_blocked_paths": len(blocked) >= 3,
        "sandbox_pass_fail_visible": sandbox_summary.get("pass_count", 0) > 0
        and sandbox_summary.get("fail_count", 0) > 0,
        "api_status_visible": api_dry_run_report.get("real_user_dry_run_status") == "blocked_missing_metadata",
        "fixture_boundary_visible": concrete_brief.get("source_mode") == "approved_fixture_not_live_market_data",
        "every_candidate_has_user_action": all(bool(item.get("user_action")) for item in packet_items),
        "every_candidate_has_evidence": all(bool(item.get("evidence_refs")) for item in packet_items),
        "no_live_price": concrete_brief.get("safety", {}).get("no_live_price") is True,
        "no_position_size": concrete_brief.get("safety", {}).get("no_position_size") is True,
        "manual_external_execution_only": concrete_brief.get("safety", {}).get("manual_external_execution_only") is True,
        "no_real_trade": concrete_brief.get("safety", {}).get("no_real_trade") is True
        and api_dry_run_report.get("safety", {}).get("no_real_trade") is True,
        "no_broker_api": concrete_brief.get("safety", {}).get("no_broker_api") is True
        and api_dry_run_report.get("safety", {}).get("no_broker_api") is True,
        "no_trading_webhook": api_dry_run_report.get("safety", {}).get("no_trading_webhook") is True,
        "production_records_not_written": concrete_brief.get("production_records_written") is False
        and api_dry_run_report.get("production_records_written") is False,
        "dashboard_contract_unchanged": concrete_brief.get("dashboard_contract_changed") is False
        and api_dry_run_report.get("dashboard_contract_changed") is False,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": "V2.9-A Current User Decision Packet",
        "packet_type": "current_simulation_user_decision_packet",
        "run_id": run_id,
        "generated_at": generated_at or _now_iso(),
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_count": len(candidates),
            "blocked_count": len(blocked),
            "candidate_markets": candidate_markets,
            "blocked_markets": blocked_markets,
            "candidate_symbols": [item.get("symbol") for item in candidates],
            "sandbox_pass_count": sandbox_summary.get("pass_count"),
            "sandbox_fail_count": sandbox_summary.get("fail_count"),
            "passing_hypotheses": sandbox_summary.get("passing_hypotheses", []),
            "failing_hypotheses": sandbox_summary.get("failing_hypotheses", []),
            "real_user_api_status": api_dry_run_report.get("real_user_dry_run_status"),
            "fixture_api_bound_markets": api_summary.get("fixture_bound_markets", []),
        },
        "user_boundary": {
            "what_you_can_do_now": [
                "查看 simulation_candidate 项，作为人工观察和纸面验证清单。",
                "在外部行情/券商软件手动核对实时价格、流动性、公司事件和持仓风险。",
                "如果你决定实际操作，只能在 Aegis 外部手动下单。",
                "把截图、成交记录或文字决策回传给 Aegis 作为 evidence input。",
            ],
            "what_aegis_does_not_do": [
                "不自动下单。",
                "不连接 Broker API。",
                "不使用 trading webhook。",
                "不提供实时价格或仓位数量。",
                "不把 fixture candidates 冒充为 live API candidates。",
            ],
            "current_blocker": (
                "真实用户 API 仍缺 config/external_api_connectors.local.json 的非敏感 metadata "
                "和本机 env var，因此 live API-backed candidates 尚不可声明。"
            ),
        },
        "items": packet_items,
        "checks": checks,
        "safety": {
            "simulation_only": True,
            "manual_external_execution_only": True,
            "fixture_not_live_market_data": True,
            "real_user_api_blocked_missing_metadata": True,
            "no_live_price": True,
            "no_position_size": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_production_records_mutation": True,
            "dashboard_contract_unchanged": True,
        },
    }


def _render_markdown(packet: Mapping) -> str:
    lines = [
        "# V2.9-A Current User Decision Packet",
        "",
        f"- status: `{packet.get('overall_status')}`",
        f"- run_id: `{packet.get('run_id')}`",
        f"- candidate_count: `{packet.get('summary', {}).get('candidate_count')}`",
        f"- blocked_count: `{packet.get('summary', {}).get('blocked_count')}`",
        f"- candidate_markets: `{packet.get('summary', {}).get('candidate_markets')}`",
        f"- real_user_api_status: `{packet.get('summary', {}).get('real_user_api_status')}`",
        "",
        "## 你现在可以怎么用",
        "",
    ]
    for action in packet.get("user_boundary", {}).get("what_you_can_do_now", []):
        lines.append(f"- {action}")
    lines.extend(["", "## 边界", ""])
    for boundary in packet.get("user_boundary", {}).get("what_aegis_does_not_do", []):
        lines.append(f"- {boundary}")
    lines.extend(["", f"当前阻塞：{packet.get('user_boundary', {}).get('current_blocker')}", "", "## 候选与阻断", ""])
    for item in packet.get("items", []):
        lines.extend(
            [
                f"### {item.get('symbol')}",
                "",
                f"- market: `{item.get('market')}`",
                f"- status: `{item.get('decision_packet_status')}`",
                f"- source_mode: `{item.get('source_mode')}`",
                f"- user_action: {item.get('user_action')}",
                f"- blocked_by: `{', '.join(item.get('blocked_by') or []) or 'none'}`",
                f"- evidence_refs: `{len(item.get('evidence_refs') or [])}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
    concrete_brief_json: Path = DEFAULT_CONCRETE_BRIEF_JSON,
    sandbox_report_json: Path = DEFAULT_SANDBOX_REPORT_JSON,
    api_dry_run_json: Path = DEFAULT_API_DRY_RUN_JSON,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    concrete_brief = _load_json(concrete_brief_json)
    sandbox_report = _load_json(sandbox_report_json)
    api_dry_run_report = _load_json(api_dry_run_json)
    packet = _build_packet(
        concrete_brief=concrete_brief,
        sandbox_report=sandbox_report,
        api_dry_run_report=api_dry_run_report,
        run_id=run_id,
    )
    packet_json = run_dir / "current_user_decision_packet.json"
    packet_md = run_dir / "current_user_decision_packet.md"
    packet_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    packet_md.write_text(_render_markdown(packet), encoding="utf-8")

    checks = packet["checks"] | {
        "packet_status_pass": packet["overall_status"] == "PASS",
        "packet_json_written": packet_json.exists(),
        "packet_md_written": packet_md.exists(),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.9-A acceptance checks failed: " + ", ".join(failed))

    report = {
        **packet,
        "command": command,
        "run_dir": str(run_dir),
        "packet_json": str(packet_json),
        "packet_md": str(packet_md),
        "source_concrete_brief_json": str(concrete_brief_json),
        "source_sandbox_report_json": str(sandbox_report_json),
        "source_api_dry_run_json": str(api_dry_run_json),
        "checks": checks,
        "hashes": {
            "packet_json": _sha256(packet_json),
            "packet_md": _sha256(packet_md),
            "source_concrete_brief_json": _sha256(concrete_brief_json),
            "source_sandbox_report_json": _sha256(sandbox_report_json),
            "source_api_dry_run_json": _sha256(api_dry_run_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.9-A Current User Decision Packet",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"packet_json={report['packet_json']}",
                f"packet_json_sha256={report['hashes']['packet_json']}",
                "network_used=false",
                "production_records_written=false",
                "dashboard_contract_changed=false",
                "simulation_only=true",
                "manual_external_execution_only=true",
                "fixture_not_live_market_data=true",
                "real_user_api_blocked_missing_metadata=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "no_order_placement=true",
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
    parser.add_argument("--concrete-brief-json", type=Path, default=DEFAULT_CONCRETE_BRIEF_JSON)
    parser.add_argument("--sandbox-report-json", type=Path, default=DEFAULT_SANDBOX_REPORT_JSON)
    parser.add_argument("--api-dry-run-json", type=Path, default=DEFAULT_API_DRY_RUN_JSON)
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
            concrete_brief_json=args.concrete_brief_json,
            sandbox_report_json=args.sandbox_report_json,
            api_dry_run_json=args.api_dry_run_json,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.9-A Current User Decision Packet",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.9-A Current User Decision Packet FAIL: {exc}")
        return 1

    print(f"V2.9-A Current User Decision Packet PASS run_id={report['run_id']} report={reports_dir / REPORT_JSON if False else args.reports_dir / REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

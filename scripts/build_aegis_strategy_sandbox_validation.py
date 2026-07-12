#!/usr/bin/env python3
"""Build a strategy sandbox coverage report for current Aegis candidates.

This script does not run live trading, mutate paper trades, or call any
provider. It only connects the current research candidates to existing
historical evidence so the Dashboard can show what is validated and what still
needs point-in-time case assembly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
PROCESSED = ROOT / "data" / "processed" / "aegis_strategy_sandbox_validation"

INPUT = REPORTS / "aegis_strategy_validation_input_latest.json"
PIT = REPORTS / "a_share_point_in_time_rolling_backtest_latest.json"
LEGACY = REPORTS / "v2_14_c_refreshed_candidate_historical_sandbox_latest.json"

OUT_JSON = REPORTS / "aegis_strategy_sandbox_validation_latest.json"
OUT_MD = REPORTS / "aegis_strategy_sandbox_validation_latest.md"
PASS_MARKER = REPORTS / "AEGIS_STRATEGY_SANDBOX_VALIDATION_PASS.marker"
FAIL_MARKER = REPORTS / "AEGIS_STRATEGY_SANDBOX_VALIDATION_FAIL.marker"

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
    "feedback_events_jsonl": ROOT / "data" / "records" / "aegis_stock_feedback_events.jsonl",
}

A_SHARE_PROXY_IDS = {"qvm", "low_vol_momentum", "a_share_short_momentum"}
H_US_PENDING_IDS = {"qvm", "low_vol_momentum", "hk_smart_beta", "growth_breakout"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(path: Path) -> dict[str, Any]:
    return {
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path),
    }


def fingerprints(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    return {name: fingerprint(path) for name, path in paths.items()}


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_ref(label: str, path: Path) -> str:
    digest = sha256(path)
    return f"{label}:{path.name}:{digest or 'missing'}"


def pit_ready(pit: dict[str, Any] | None) -> bool:
    if not pit:
        return False
    return (
        pit.get("point_in_time_required") is True
        and pit.get("static_snapshot_backtest") is False
        and pit.get("lookahead_bias_control_passed") is True
        and int(pit.get("passed_periods_count") or 0) > 0
    )


def classify_item(item: dict[str, Any], pit: dict[str, Any] | None, legacy: dict[str, Any] | None) -> dict[str, Any]:
    strategy_ids = set(item.get("matched_strategy_ids") or [])
    refs = [source_ref("strategy_input", INPUT)]
    notes: list[str] = []
    blockers: list[str] = []
    status = "pending_history_cases"
    coverage_tier = "not_validated"
    confidence = "low"

    if item.get("market") == "A" and pit_ready(pit) and strategy_ids.intersection(A_SHARE_PROXY_IDS):
        status = "proxy_validated_needs_candidate_specific_cases"
        coverage_tier = "point_in_time_proxy"
        confidence = "medium_low"
        refs.append(source_ref("a_share_point_in_time_rolling_backtest", PIT))
        notes.append("A股已有按历史时点取数的滚动回测，可作为策略族代理证据。")
        blockers.append("尚未为当前单只候选生成逐标的 point-in-time 历史 case。")
    elif item.get("market") in {"US", "HK"} and strategy_ids.intersection(H_US_PENDING_IDS):
        status = "pending_h_us_history_case_assembly"
        coverage_tier = "needs_case_assembly"
        confidence = "low"
        refs.append(source_ref("legacy_refreshed_candidate_sandbox", LEGACY))
        notes.append("H/US 当前具备候选和资讯层，但仍需补逐标的历史沙盘。")
        blockers.append("缺少当前候选对应的 H/US point-in-time 历史 case。")
    else:
        blockers.append("当前策略信号尚未找到可复用历史验证证据。")

    if "ai_photonics_supply_chain" in strategy_ids:
        status = "pending_theme_history_case_assembly"
        coverage_tier = "theme_research_only"
        confidence = "low"
        notes.append("AI 光子学主题只能作为研究线索，必须等待主题历史样本和估值过热否决验证。")
        blockers.append("主题策略未完成历史样本集合。")

    return {
        "symbol": item.get("symbol"),
        "name": item.get("name"),
        "market": item.get("market"),
        "score": item.get("score"),
        "matched_strategy_ids": item.get("matched_strategy_ids") or [],
        "coverage_tier": coverage_tier,
        "strategy_validation_status": status,
        "confidence": confidence,
        "evidence_refs": refs,
        "notes": notes,
        "blockers": blockers,
        "user_facing_suggestion_allowed": False,
        "simulation_research_only": True,
        "real_trade_allowed": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Aegis Strategy Sandbox Validation",
        "",
        f"- Status: {report['status']}",
        f"- Generated At: {report['generated_at']}",
        f"- Candidate Count: {summary['candidate_count']}",
        f"- Proxy Validated Count: {summary['proxy_validated_count']}",
        f"- Pending Case Count: {summary['pending_case_count']}",
        f"- Direct Candidate Backtest Count: {summary['direct_candidate_backtest_count']}",
        f"- User-Facing Suggestion Allowed: {summary['user_facing_suggestion_allowed']}",
        "",
        "## Safety",
        "",
    ]
    for key, value in report["safety"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Items", ""])
    for item in report["items"]:
        lines.append(
            f"- {item['symbol']} {item['name']} ({item['market']}): "
            f"{item['strategy_validation_status']} / {item['coverage_tier']} / {item['confidence']}"
        )
        for blocker in item["blockers"]:
            lines.append(f"  - blocker: {blocker}")
    lines.append("")
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    validation_input = load_json(INPUT)
    pit = load_json(PIT)
    legacy = load_json(LEGACY)
    before = fingerprints(RECORD_PATHS)

    if not validation_input or validation_input.get("status") != "READY":
        items: list[dict[str, Any]] = []
        status = "FAIL"
        errors = ["strategy validation input missing or not READY"]
    else:
        items = [classify_item(item, pit, legacy) for item in validation_input.get("items", [])]
        status = "PASS"
        errors = []

    after = fingerprints(RECORD_PATHS)
    proxy_count = sum(1 for item in items if item["coverage_tier"] == "point_in_time_proxy")
    pending_count = sum(1 for item in items if item["coverage_tier"] != "point_in_time_proxy")
    run_id = f"aegis_strategy_sandbox_validation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = PROCESSED / run_id

    report: dict[str, Any] = {
        "type": "aegis_strategy_sandbox_validation",
        "status": status,
        "generated_at": now_iso(),
        "run_id": run_id,
        "summary": {
            "candidate_count": len(items),
            "proxy_validated_count": proxy_count,
            "pending_case_count": pending_count,
            "direct_candidate_backtest_count": 0,
            "point_in_time_backtest_available": pit_ready(pit),
            "lookahead_bias_control_passed": bool(pit and pit.get("lookahead_bias_control_passed") is True),
            "user_facing_suggestion_allowed": False,
            "next_stage": "strategy-specific historical case assembly",
        },
        "items": items,
        "source_reports": {
            "strategy_validation_input": str(INPUT),
            "a_share_point_in_time_rolling_backtest": str(PIT),
            "legacy_refreshed_candidate_historical_sandbox": str(LEGACY),
        },
        "source_hashes": {
            "strategy_validation_input": sha256(INPUT),
            "a_share_point_in_time_rolling_backtest": sha256(PIT),
            "legacy_refreshed_candidate_historical_sandbox": sha256(LEGACY),
        },
        "checks": {
            "strategy_validation_input_ready": bool(validation_input and validation_input.get("status") == "READY"),
            "source_hashes_recorded": True,
            "point_in_time_backtest_referenced": pit_ready(pit),
            "direct_candidate_backtest_not_claimed": True,
            "user_facing_suggestion_blocked": True,
            "production_records_unchanged": before == after,
            "network_not_used": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
        },
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "real_trade_allowed": False,
        },
        "production_record_files_before": before,
        "production_record_files_after": after,
        "errors": errors,
        "run_dir": str(run_dir),
    }
    if not all(report["checks"].values()):
        report["status"] = "FAIL"
    return report


def main() -> int:
    report = build_report()
    run_dir = Path(report["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)

    run_json = run_dir / "strategy_sandbox_validation.json"
    run_md = run_dir / "strategy_sandbox_validation.md"
    write_json(run_json, report)
    run_md.write_text(render_markdown(report), encoding="utf-8")
    write_json(OUT_JSON, report)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")

    marker = PASS_MARKER if report["status"] == "PASS" else FAIL_MARKER
    stale = FAIL_MARKER if marker == PASS_MARKER else PASS_MARKER
    if stale.exists():
        stale.unlink()
    marker.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"exit_code={0 if report['status'] == 'PASS' else 1}",
                f"report_json={OUT_JSON}",
                f"report_json_sha256={sha256(OUT_JSON)}",
                f"report_md={OUT_MD}",
                f"report_md_sha256={sha256(OUT_MD)}",
                f"candidate_count={report['summary']['candidate_count']}",
                f"proxy_validated_count={report['summary']['proxy_validated_count']}",
                f"pending_case_count={report['summary']['pending_case_count']}",
                "direct_candidate_backtest_count=0",
                "network_used=false",
                "user_facing_suggestion_allowed=false",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_webhook=true",
                "no_order_placement=true",
                "no_position_size=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "report_json": str(OUT_JSON),
                "candidate_count": report["summary"]["candidate_count"],
                "proxy_validated_count": report["summary"]["proxy_validated_count"],
                "pending_case_count": report["summary"]["pending_case_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

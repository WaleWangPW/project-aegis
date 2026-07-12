#!/usr/bin/env python3
"""Run Project Aegis daily real-scene pilot.

This is the daily usable entry for simulation-only stock research. It refreshes
candidate evidence, rebuilds Dashboard/card artifacts, optionally sends the
stock-assistant cards, and writes an auditable pilot report.

It never places orders, calls brokers, changes holdings, creates paper trades,
or calls trading webhooks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUT_JSON = REPORTS / "aegis_daily_real_scene_pilot_latest.json"
OUT_MD = REPORTS / "aegis_daily_real_scene_pilot_latest.md"
PASS_MARKER = REPORTS / "AEGIS_DAILY_REAL_SCENE_PILOT_PASS.marker"
FAIL_MARKER = REPORTS / "AEGIS_DAILY_REAL_SCENE_PILOT_FAIL.marker"

REPORT_PATHS = {
    "stock_selection_workbench": REPORTS / "stock_selection_workbench_latest.json",
    "h_us_daily_bar_refresh": REPORTS / "aegis_h_us_candidate_daily_bars_refresh_latest.json",
    "strategy_specific_historical_cases": REPORTS / "aegis_strategy_specific_historical_cases_latest.json",
    "strategy_specific_case_evaluation": REPORTS / "aegis_strategy_specific_case_evaluation_latest.json",
    "stock_assistant_cards_report": REPORTS / "aegis_stock_assistant_feishu_cards_latest_report.json",
    "stock_assistant_cards": REPORTS / "aegis_stock_assistant_feishu_cards_latest.json",
    "stock_assistant_send": REPORTS / "aegis_stock_assistant_feishu_send_latest.json",
    "feedback_latest": REPORTS / "aegis_stock_feedback_latest.json",
    "dashboard_index": ROOT / "dashboard" / "index.html",
    "dashboard_css": ROOT / "dashboard" / "v2.css",
    "dashboard_js": ROOT / "dashboard" / "v2.js",
}

RECORD_PATHS = {
    "recommendations_jsonl": ROOT / "data" / "records" / "recommendations.jsonl",
    "paper_trades_jsonl": ROOT / "data" / "records" / "paper_trades.jsonl",
    "reviews_jsonl": ROOT / "data" / "records" / "reviews.jsonl",
    "memory_jsonl": ROOT / "data" / "records" / "memory.jsonl",
    "investment_memory_jsonl": ROOT / "data" / "records" / "investment_memory.jsonl",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


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
    return {key: fingerprint(path) for key, path in paths.items()}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {"_json_error": "invalid_json"}


def run_command(label: str, cmd: list[str], timeout: int = 240) -> dict[str, Any]:
    started = now_iso()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "label": label,
        "command": cmd,
        "started_at": started,
        "finished_at": now_iso(),
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2400:],
        "stderr_tail": (proc.stderr or "")[-2400:],
    }


def http_head(url: str) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=5) as response:
            return {"url": url, "ok": response.status == 200, "status": response.status}
    except Exception as exc:  # noqa: BLE001 - report sanitized local serving issue.
        return {"url": url, "ok": False, "error": f"{type(exc).__name__}: {str(exc)[:180]}"}


def report_status(path: Path) -> str | None:
    payload = load_json(path)
    if "status" in payload:
        return str(payload.get("status"))
    if "send_status" in payload:
        return str(payload.get("send_status"))
    return None


def build_summary(send_mode: str) -> dict[str, Any]:
    workbench = load_json(REPORT_PATHS["stock_selection_workbench"])
    case_eval = load_json(REPORT_PATHS["strategy_specific_case_evaluation"])
    send = load_json(REPORT_PATHS["stock_assistant_send"])
    cards = load_json(REPORT_PATHS["stock_assistant_cards_report"])
    return {
        "send_mode": send_mode,
        "candidate_summary": workbench.get("summary", {}),
        "case_evaluation_summary": case_eval.get("summary", {}),
        "card_count": cards.get("card_count"),
        "send_status": send.get("send_status"),
        "sent_count": send.get("sent_count"),
        "failed_count": send.get("failed_count"),
        "transport": send.get("transport"),
        "next_user_action": [
            "Open http://localhost:8080/dashboard/index.html",
            "Read 今日结论 and 风险阻塞 first",
            "Review Top 3 candidates only",
            "Use stock assistant buttons to record watch / ignore / more-news feedback",
            "If you place any real order externally, record it manually as external evidence only",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Aegis Daily Real-Scene Pilot",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Dashboard: `{report['dashboard_check'].get('url')}`",
        f"- Dashboard HTTP OK: `{report['dashboard_check'].get('ok')}`",
        f"- Send Mode: `{summary.get('send_mode')}`",
        f"- Stock Assistant Send: `{summary.get('send_status')}` sent=`{summary.get('sent_count')}` failed=`{summary.get('failed_count')}`",
        "",
        "## Candidate Summary",
        "",
        f"- Total candidates: `{summary.get('candidate_summary', {}).get('total_candidates')}`",
        f"- Research candidates: `{summary.get('candidate_summary', {}).get('research_candidate_count')}`",
        f"- News enriched: `{summary.get('candidate_summary', {}).get('news_enriched_count')}`",
        f"- Markets passed: `{summary.get('candidate_summary', {}).get('markets_passed')}`",
        "",
        "## Case Evaluation",
        "",
        f"- Evaluated candidates: `{summary.get('case_evaluation_summary', {}).get('candidate_count')}`",
        f"- Continue simulation research: `{summary.get('case_evaluation_summary', {}).get('simulation_research_candidate_count')}`",
        f"- Watch only: `{summary.get('case_evaluation_summary', {}).get('watch_only_count')}`",
        f"- Downgraded: `{summary.get('case_evaluation_summary', {}).get('downgraded_count')}`",
        "",
        "## Commands",
        "",
    ]
    for item in report["commands"]:
        lines.append(f"- `{item['label']}` exit_code=`{item['exit_code']}`")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Simulation/research only.",
            "- No broker API.",
            "- No real order placement.",
            "- No trading webhook.",
            "- No position sizing.",
            "- Feedback buttons record evidence only.",
            "",
            "## Next User Action",
            "",
        ]
    )
    for action in summary["next_user_action"]:
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dashboard-url", default="http://localhost:8080/dashboard/index.html")
    parser.add_argument("--no-send", action="store_true", help="Build cards but do not call the sender.")
    parser.add_argument("--send-dry-run", action="store_true", help="Call sender in dry-run mode.")
    parser.add_argument("--skip-h-us-refresh", action="store_true", help="Skip H/US daily-bar refresh.")
    args = parser.parse_args()

    commands: list[dict[str, Any]] = []
    before_records = fingerprints(RECORD_PATHS)
    py = sys.executable

    plan: list[tuple[str, list[str], int, bool]] = [
        ("build_stock_selection_workbench", [py, "scripts/build_stock_selection_workbench_v2_15_a.py"], 120, True),
    ]
    if not args.skip_h_us_refresh:
        plan.append(("refresh_h_us_daily_bars", [py, "scripts/refresh_aegis_h_us_candidate_daily_bars.py"], 360, True))
    plan.extend(
        [
            (
                "build_strategy_specific_historical_cases",
                [py, "scripts/build_aegis_strategy_specific_historical_cases.py"],
                120,
                True,
            ),
            (
                "evaluate_strategy_specific_cases",
                [py, "scripts/evaluate_aegis_strategy_specific_cases.py"],
                120,
                True,
            ),
            ("build_stock_assistant_cards", [py, "scripts/build_aegis_stock_feishu_cards.py"], 120, True),
        ]
    )
    if not args.no_send:
        send_cmd = [py, "scripts/send_aegis_stock_feishu_cards_via_stock_assistant.py"]
        if args.send_dry_run:
            send_cmd.append("--dry-run")
        plan.append(("send_stock_assistant_cards", send_cmd, 180, False))

    fatal_failed = False
    for label, cmd, timeout, fatal in plan:
        result = run_command(label, cmd, timeout=timeout)
        commands.append(result)
        if result["exit_code"] != 0 and fatal:
            fatal_failed = True
            break

    dashboard_check = http_head(args.dashboard_url)
    after_records = fingerprints(RECORD_PATHS)
    report_files = fingerprints(REPORT_PATHS)
    send_mode = "skipped" if args.no_send else ("dry_run" if args.send_dry_run else "send_if_target_available")
    summary = build_summary(send_mode=send_mode)

    required_statuses = {
        "strategy_specific_historical_cases": "PASS",
        "strategy_specific_case_evaluation": "PASS",
        "stock_assistant_cards_report": "PASS",
    }
    status_checks = {
        key: report_status(REPORT_PATHS[key]) == expected for key, expected in required_statuses.items()
    }
    status_checks["dashboard_http_ok"] = bool(dashboard_check.get("ok"))
    status_checks["critical_commands_passed"] = not fatal_failed
    status_checks["production_records_unchanged"] = before_records == after_records
    status_checks["real_trade_allowed_false"] = summary.get("candidate_summary", {}).get("real_trade_allowed") is False
    status_checks["case_user_facing_suggestion_disabled"] = (
        summary.get("case_evaluation_summary", {}).get("user_facing_suggestion_allowed") is False
    )

    report = {
        "type": "aegis_daily_real_scene_pilot",
        "status": "PASS" if all(status_checks.values()) else "FAIL",
        "generated_at": now_iso(),
        "dashboard_check": dashboard_check,
        "commands": commands,
        "summary": summary,
        "checks": status_checks,
        "report_files": report_files,
        "production_record_files_before": before_records,
        "production_record_files_after": after_records,
        "safety": {
            "simulation_only": True,
            "research_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "feedback_evidence_only": True,
            "real_trade_allowed": False,
        },
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
                "simulation_only=true",
                "real_trade_allowed=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"status={report['status']}")
    print(f"report_json={OUT_JSON}")
    print(f"report_json_sha256={sha256(OUT_JSON)}")
    print(f"report_md={OUT_MD}")
    print(f"dashboard_ok={dashboard_check.get('ok')}")
    print(f"send_status={summary.get('send_status')}")
    print(f"sent_count={summary.get('sent_count')}")
    print(f"failed_count={summary.get('failed_count')}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

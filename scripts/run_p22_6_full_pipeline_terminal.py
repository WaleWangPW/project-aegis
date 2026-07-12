from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from dashboard_contract import inspect_dashboard

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
DASHBOARD = ROOT / "dashboard" / "index.html"

PASS_MARKER = REPORTS / "P22_6_FULL_PIPELINE_PASS.marker"
FAIL_MARKER = REPORTS / "P22_6_FULL_PIPELINE_FAIL.marker"
FAIL_REASON = REPORTS / "P22_6_FULL_PIPELINE_FAIL_REASON.md"
EVIDENCE_JSON = REPORTS / "p22_6_full_pipeline_evidence.json"
EVIDENCE_MD = REPORTS / "p22_6_full_pipeline_evidence.md"

SECRET_RE = re.compile(
    r"(?i)(Bearer\s+[A-Za-z0-9._-]{12,}|Authorization\s*[:=]\s*[^\s]+|"
    r"https?://[^\s\"']*(open\.feishu\.cn|hooks)[^\s\"']*|"
    r"(token|api[_-]?key|cookie)\s*[:=]\s*[A-Za-z0-9._-]{12,})"
)

def now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def sanitize(text: str) -> str:
    return SECRET_RE.sub("***REDACTED***", text or "")[-2500:]

def run_cmd(cmd: str, timeout: int = 1800) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": sanitize(proc.stdout),
        "stderr_tail": sanitize(proc.stderr),
        "result": "PASS" if proc.returncode == 0 else "FAIL",
    }

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def fail(reason: str, commands: list[dict[str, Any]]) -> int:
    FAIL_MARKER.write_text("FAIL\n", encoding="utf-8")
    if PASS_MARKER.exists():
        PASS_MARKER.unlink()

    FAIL_REASON.write_text(
        "# P22.6 Full Pipeline FAIL Reason\n\n"
        f"{reason}\n\n"
        "## Commands\n\n"
        + "\n".join(f"- {c['command']}: exit={c['exit_code']}" for c in commands)
        + "\n",
        encoding="utf-8",
    )
    write_evidence(False, reason, commands)
    return 1

def dashboard_checks() -> dict[str, bool]:
    text = DASHBOARD.read_text(encoding="utf-8", errors="ignore") if DASHBOARD.exists() else ""
    contract = inspect_dashboard(DASHBOARD, ROOT / "dashboard" / "v2.js", ROOT / "dashboard" / "v2.css")
    if contract["detected_dashboard_type"] == "ceo_daily_brief_v2":
        return {
            "dashboard_exists": DASHBOARD.exists(),
            "dashboard_contract_v2": contract["overall_verdict"] == "PASS",
            "no_secret_value_detected": not bool(SECRET_RE.search(text)),
            "no_send_call_detected": ".post(" not in text and "requests.post" not in text,
            "no_trading_call_detected": "broker.buy" not in text and "broker.sell" not in text,
        }
    return {
        "dashboard_exists": DASHBOARD.exists(),
        "health_light_present": "Project Aegis 健康灯" in text,
        "single_backtest_present": "A股 Watchlist 单次回测 Dry-run" in text,
        "backtest_history_present": "A股 Watchlist 回测历史" in text,
        "single_backtest_json_fetch_present": "a_share_backtest_dry_run_latest.json" in text,
        "history_json_fetch_present": "a_share_backtest_history_latest.json" in text,
        "lookahead_warning_present": "lookahead bias" in text,
        "no_secret_value_detected": not bool(SECRET_RE.search(text)),
        "no_send_call_detected": ".post(" not in text and "requests.post" not in text,
        "no_trading_call_detected": "broker.buy" not in text and "broker.sell" not in text,
    }

def collect_summary() -> dict[str, Any]:
    out: dict[str, Any] = {}

    health_path = REPORTS / "aegis_health_status_latest.json"
    backtest_path = REPORTS / "a_share_backtest_dry_run_latest.json"
    history_path = REPORTS / "a_share_backtest_history_latest.json"

    if health_path.exists():
        health = load_json(health_path)
        out["health_status"] = health.get("health_status")
        out["health_label"] = health.get("health_label")
        out["gate_overall_verdict"] = health.get("gate_overall_verdict")

    if backtest_path.exists():
        bt = load_json(backtest_path)
        m = bt.get("portfolio_metrics") or {}
        b = bt.get("benchmark_metrics") or {}
        out["backtest"] = {
            "strategy_id": bt.get("strategy_id"),
            "selected_symbols_count": bt.get("selected_symbols_count"),
            "valid_price_series_count": bt.get("valid_price_series_count"),
            "total_return": m.get("total_return"),
            "annualized_return": m.get("annualized_return"),
            "max_drawdown": m.get("max_drawdown"),
            "volatility": m.get("volatility"),
            "sharpe": m.get("sharpe"),
            "win_rate": m.get("win_rate"),
            "benchmark_total_return": b.get("total_return") if isinstance(b, dict) else None,
            "excess_return": bt.get("excess_return"),
            "dry_run": bt.get("dry_run"),
            "sent": bt.get("sent"),
            "trading_called": bt.get("trading_called"),
        }

    if history_path.exists():
        hist = load_json(history_path)
        out["history"] = {
            "runs_count": hist.get("runs_count"),
            "latest_run_id": hist.get("latest_run_id"),
            "latest_result": hist.get("latest_result"),
            "retention_limit": hist.get("retention_limit"),
        }

    return out

def write_evidence(success: bool, reason: str, commands: list[dict[str, Any]]) -> None:
    checks = {
        "p22_2_pass_marker": (REPORTS / "P22_2_BACKTEST_DRY_RUN_PASS.marker").exists(),
        "p22_3_pass_marker": (REPORTS / "P22_3_DASHBOARD_BACKTEST_PASS.marker").exists(),
        "p22_4_pass_marker": (REPORTS / "P22_4_BACKTEST_HISTORY_PASS.marker").exists(),
        "p22_5_pass_marker": (REPORTS / "P22_5_BACKTEST_HISTORY_DASHBOARD_PASS.marker").exists(),
        "health_json_exists": (REPORTS / "aegis_health_status_latest.json").exists(),
        "backtest_json_exists": (REPORTS / "a_share_backtest_dry_run_latest.json").exists(),
        "backtest_history_json_exists": (REPORTS / "a_share_backtest_history_latest.json").exists(),
    }
    checks.update(dashboard_checks())

    evidence = {
        "project": "Project Aegis",
        "type": "p22_6_full_pipeline",
        "generated_at": now(),
        "success": success,
        "reason": reason,
        "commands": commands,
        "checks": checks,
        "summary": collect_summary(),
        "safety": {
            "dry_run": True,
            "sent": False,
            "webhook_called": False,
            "trading_called": False,
            "cron_modified": False,
        },
    }
    write_json(EVIDENCE_JSON, evidence)

    md = [
        "# Project Aegis P22.6 Full Pipeline Evidence",
        "",
        f"- success: {success}",
        f"- reason: {reason or 'N/A'}",
        "",
        "## Commands",
        "| command | exit_code | result |",
        "|---|---:|---|",
    ]
    for c in commands:
        md.append(f"| {c['command']} | {c['exit_code']} | {c['result']} |")

    md += [
        "",
        "## Checks",
        "| check | result |",
        "|---|---|",
    ]
    for k, v in checks.items():
        md.append(f"| {k} | {'PASS' if v else 'FAIL'} |")

    summary = evidence["summary"]
    md += [
        "",
        "## Summary",
        f"- health_status: {summary.get('health_status')}",
        f"- health_label: {summary.get('health_label')}",
        f"- gate_overall_verdict: {summary.get('gate_overall_verdict')}",
        f"- history: {summary.get('history')}",
        f"- backtest: {summary.get('backtest')}",
        "",
        "## Safety",
        "- dry_run: true",
        "- sent: false",
        "- webhook_called: false",
        "- trading_called: false",
        "- cron_modified: false",
    ]
    EVIDENCE_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)

    for p in [PASS_MARKER, FAIL_MARKER]:
        if p.exists():
            p.unlink()

    commands: list[dict[str, Any]] = []

    repo_required = [
        ROOT / "Makefile",
        DASHBOARD,
        ROOT / ".venv/bin/python",
        REPORTS,
    ]
    missing = [str(p.relative_to(ROOT)) for p in repo_required if not p.exists()]
    if missing:
        return fail("repo sanity failed: " + ", ".join(missing), commands)

    chain = [
        "make validate-a-share-strategy-definition",
        "make validate-a-share-backtest-dry-run",
        "make p22-4-filemode",
        "make p22-5-filemode",
        "make validate-a-share-backtest-history",
        "make validate-aegis-health-status",
        "make verify-aegis-evidence-gate",
    ]

    for cmd in chain:
        r = run_cmd(cmd)
        commands.append(r)
        if r["exit_code"] != 0:
            return fail(f"command failed: {cmd}", commands)

    checks = {
        "p22_2": (REPORTS / "P22_2_BACKTEST_DRY_RUN_PASS.marker").exists(),
        "p22_3": (REPORTS / "P22_3_DASHBOARD_BACKTEST_PASS.marker").exists(),
        "p22_4": (REPORTS / "P22_4_BACKTEST_HISTORY_PASS.marker").exists(),
        "p22_5": (REPORTS / "P22_5_BACKTEST_HISTORY_DASHBOARD_PASS.marker").exists(),
        **dashboard_checks(),
    }

    failed = [k for k, v in checks.items() if not v]
    if failed:
        return fail("final checks failed: " + ", ".join(failed), commands)

    PASS_MARKER.write_text("PASS\n", encoding="utf-8")
    if FAIL_MARKER.exists():
        FAIL_MARKER.unlink()
    if FAIL_REASON.exists():
        FAIL_REASON.unlink()

    write_evidence(True, "", commands)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

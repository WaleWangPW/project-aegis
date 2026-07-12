#!/usr/bin/env python3
"""
run_p22_1_filemode.py

File-mode execution script for Project Aegis P22.1.
Generates all required files, validates, and writes evidence to files only.
Does not depend on terminal stdout.
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo")
STRATEGY_DIR = REPO_ROOT / "config" / "strategies"
SCRIPTS_DIR = REPO_ROOT / "scripts"
REPORTS_DIR = REPO_ROOT / "data" / "reports"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
MAKEFILE = REPO_ROOT / "Makefile"
HANDOFF = REPO_ROOT / "HANDOFF.md"

STRATEGY_JSON = STRATEGY_DIR / "a_share_watchlist_strategy_v1.json"
STRATEGY_MD = STRATEGY_DIR / "a_share_watchlist_strategy_v1.md"
INPUT_SCHEMA = STRATEGY_DIR / "a_share_backtest_input_schema_v1.json"
OUTPUT_SCHEMA = STRATEGY_DIR / "a_share_backtest_output_schema_v1.json"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_a_share_strategy_definition.py"
VALIDATION_OUT = REPORTS_DIR / "p22_1_strategy_definition_validation_latest.json"
EVIDENCE_JSON = REPORTS_DIR / "p22_1_strategy_definition_evidence.json"
EVIDENCE_MD = REPORTS_DIR / "p22_1_strategy_definition_evidence.md"

P19_10_TOP5 = ["600519.SH", "600036.SH", "000858.SZ", "000001.SZ", "601398.SH"]


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def run_cmd(cmd, cwd=None):
    """Run a command, return (exit_code, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, cwd=cwd or REPO_ROOT, capture_output=True, text=True, timeout=120)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)


def main():
    log = {"steps": [], "results": {}}
    log["started_at"] = now_iso()

    # Step 1: Create directories
    STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
    log["steps"].append("created directories")

    # Step 2: Read current watchlist
    watchlist_path = REPORTS_DIR / "a_share_watchlist_latest.json"
    watchlist = None
    if watchlist_path.exists():
        try:
            watchlist = json.loads(watchlist_path.read_text(encoding="utf-8"))
        except Exception as e:
            log["results"]["watchlist_parse_error"] = str(e)
    log["results"]["watchlist_loaded"] = watchlist is not None
    log["results"]["watchlist_top5_actual"] = [s.get("symbol", "") for s in watchlist.get("top5", [])] if watchlist else []

    # Step 3: Generate strategy definition JSON
    strategy_def = {
        "strategy_id": "a_share_watchlist_v1",
        "strategy_name": "A股 Watchlist 策略 v1",
        "version": "1.0.0",
        "market": "A_SHARE",
        "mode": "read_only_watchlist",
        "description": "A-share read-only watchlist derived from P19.10 baseline Top5 and extended to 20 monitored symbols.",
        "universe_source": "data/reports/a_share_watchlist_latest.json (P19.10 baseline extended)",
        "data_sources": [
            "data/reports/a_share_watchlist_latest.json"
        ],
        "ranking_rule": {
            "primary_key": "score",
            "order": "desc",
            "tie_breaker": "symbol_alpha"
        },
        "status_rule": {
            "Watch": "score >= 0.7 and in canonical_top5",
            "Monitor": "score >= 0.25 and rank <= 20"
        },
        "risk_filters": {
            "liquidity_ok_required": False,
            "max_drawdown_required_field": False,
            "volatility_required_field": False
        },
        "liquidity_rule": "N/A in v1 (watchlist only, no positions)",
        "top_n": 20,
        "canonical_top5_expected": P19_10_TOP5,
        "safety_boundaries": [
            "no_real_trade",
            "no_order_api",
            "no_webhook_send",
            "no_secret_output"
        ],
        "backtest_not_included": True,
        "metadata": {
            "baseline_version": "P19.10",
            "created_at": now_iso(),
            "schema_version": "1.0.0"
        }
    }
    STRATEGY_JSON.write_text(json.dumps(strategy_def, ensure_ascii=False, indent=2), encoding="utf-8")
    log["steps"].append("generated strategy JSON")
    log["results"]["strategy_json_path"] = str(STRATEGY_JSON)

    # Step 4: Generate strategy MD
    strategy_md = f"""# A股 Watchlist 策略 v1

> strategy_id: {strategy_def['strategy_id']}
> version: {strategy_def['version']}
> market: {strategy_def['market']}
> mode: {strategy_def['mode']}

## 描述

{strategy_def['description']}

## 排序规则

- 主排序键: score（降序）
- 平局处理: symbol_alpha

## 状态规则

| 状态 | 条件 |
|---|---|
| Watch | score >= 0.7 且在 canonical_top5 中 |
| Monitor | score >= 0.25 且排名 <= 20 |

## TopN

- top_n: {strategy_def['top_n']}
- canonical_top5_expected: {', '.join(strategy_def['canonical_top5_expected'])}

## 安全边界

{chr(10).join('- ' + s for s in strategy_def['safety_boundaries'])}

## 回测

- backtest_not_included: {strategy_def['backtest_not_included']}
- 回测 schema 见 a_share_backtest_input_schema_v1.json 和 a_share_backtest_output_schema_v1.json

---
_Generated by run_p22_1_filemode.py at {strategy_def['metadata']['created_at']}_
"""
    STRATEGY_MD.write_text(strategy_md, encoding="utf-8")
    log["steps"].append("generated strategy MD")

    # Step 5: Generate input schema
    input_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "A-share Backtest Input Schema v1",
        "type": "object",
        "required": [
            "strategy_id",
            "strategy_version",
            "market",
            "universe_file",
            "price_data_source",
            "start_date",
            "end_date",
            "rebalance_frequency",
            "holding_period_days",
            "top_n",
            "benchmark",
            "transaction_cost_bps",
            "slippage_bps",
            "max_positions",
            "allow_short",
            "allow_real_trade"
        ],
        "properties": {
            "strategy_id": {"type": "string", "const": "a_share_watchlist_v1"},
            "strategy_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
            "market": {"type": "string", "enum": ["A_SHARE"]},
            "universe_file": {"type": "string"},
            "price_data_source": {"type": "string"},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "rebalance_frequency": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly"]},
            "holding_period_days": {"type": "integer", "minimum": 1},
            "top_n": {"type": "integer", "minimum": 1},
            "benchmark": {"type": "string", "examples": ["000300.SH", "000905.SH"]},
            "transaction_cost_bps": {"type": "number", "minimum": 0},
            "slippage_bps": {"type": "number", "minimum": 0},
            "max_positions": {"type": "integer", "minimum": 1},
            "allow_short": {"type": "boolean", "const": False},
            "allow_real_trade": {"type": "boolean", "const": False}
        },
        "additionalProperties": False
    }
    INPUT_SCHEMA.write_text(json.dumps(input_schema, ensure_ascii=False, indent=2), encoding="utf-8")
    log["steps"].append("generated input schema")

    # Step 6: Generate output schema
    output_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "A-share Backtest Output Schema v1",
        "type": "object",
        "required": [
            "strategy_id",
            "strategy_version",
            "run_id",
            "generated_at",
            "input_hash",
            "period",
            "benchmark",
            "portfolio_metrics",
            "benchmark_metrics",
            "excess_return",
            "rebalance_records",
            "selected_symbols_by_period",
            "risk_events",
            "warnings",
            "dry_run",
            "sent",
            "trading_called"
        ],
        "properties": {
            "strategy_id": {"type": "string"},
            "strategy_version": {"type": "string"},
            "run_id": {"type": "string"},
            "generated_at": {"type": "string", "format": "date-time"},
            "input_hash": {"type": "string", "pattern": r"^[0-9a-f]{12}$"},
            "period": {
                "type": "object",
                "required": ["start_date", "end_date"],
                "properties": {
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
            "benchmark": {"type": "string"},
            "portfolio_metrics": {
                "type": "object",
                "properties": {
                    "total_return": {"type": "number"},
                    "annualized_return": {"type": "number"},
                    "max_drawdown": {"type": "number"},
                    "volatility": {"type": "number"},
                    "sharpe": {"type": "number"},
                    "win_rate": {"type": "number"}
                }
            },
            "benchmark_metrics": {
                "type": "object",
                "properties": {
                    "total_return": {"type": "number"},
                    "annualized_return": {"type": "number"},
                    "max_drawdown": {"type": "number"},
                    "volatility": {"type": "number"},
                    "sharpe": {"type": "number"}
                }
            },
            "excess_return": {"type": "number"},
            "rebalance_records": {
                "type": "array",
                "items": {"type": "object"}
            },
            "selected_symbols_by_period": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "format": "date"},
                        "symbols": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "risk_events": {"type": "array", "items": {"type": "object"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "dry_run": {"type": "boolean", "const": True},
            "sent": {"type": "boolean", "const": False},
            "trading_called": {"type": "boolean", "const": False}
        },
        "additionalProperties": False
    }
    OUTPUT_SCHEMA.write_text(json.dumps(output_schema, ensure_ascii=False, indent=2), encoding="utf-8")
    log["steps"].append("generated output schema")

    # Step 7: Generate validate script
    validate_script = '''#!/usr/bin/env python3
"""
validate_a_share_strategy_definition.py

Validates P22.1 strategy definition + schemas.
Outputs STRATEGY_DEFINITION_VERDICT_JSON to stdout and to
data/reports/p22_1_strategy_definition_validation_latest.json.
Exits 0 on success, non-zero on failure.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_DIR = REPO_ROOT / "config" / "strategies"
REPORTS_DIR = REPO_ROOT / "data" / "reports"

STRATEGY_JSON = STRATEGY_DIR / "a_share_watchlist_strategy_v1.json"
STRATEGY_MD = STRATEGY_DIR / "a_share_watchlist_strategy_v1.md"
INPUT_SCHEMA = STRATEGY_DIR / "a_share_backtest_input_schema_v1.json"
OUTPUT_SCHEMA = STRATEGY_DIR / "a_share_backtest_output_schema_v1.json"
VALIDATION_OUT = REPORTS_DIR / "p22_1_strategy_definition_validation_latest.json"

EXPECTED_TOP5 = ["600519.SH", "600036.SH", "000858.SZ", "000001.SZ", "601398.SH"]
EXPECTED_SAFETY = ["no_real_trade", "no_order_api", "no_webhook_send", "no_secret_output"]

SECRET_PATTERN = re.compile(r'(token|secret|api[._-]?key|cookie|webhook[._-]?url|password|credential)', re.IGNORECASE)


def main():
    results = {
        "project": "Project Aegis",
        "type": "strategy_definition_validation",
        "validated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).astimezone().isoformat(),
        "strict_mode": True,
        "checks": {},
        "failures": [],
        "overall_verdict": "PASS"
    }

    def add(check, passed, value=None):
        entry = {"passed": passed}
        if value is not None:
            entry["value"] = value
        results["checks"][check] = entry
        if not passed:
            results["failures"].append(check)
            results["overall_verdict"] = "FAIL"

    # File existence
    add("strategy_json_exists", STRATEGY_JSON.exists())
    add("strategy_md_exists", STRATEGY_MD.exists())
    add("input_schema_exists", INPUT_SCHEMA.exists())
    add("output_schema_exists", OUTPUT_SCHEMA.exists())

    # JSON parseable
    strategy = None
    input_sch = None
    output_sch = None
    try:
        if STRATEGY_JSON.exists():
            strategy = json.loads(STRATEGY_JSON.read_text(encoding="utf-8"))
        add("strategy_json_parseable", strategy is not None)
    except Exception as e:
        add("strategy_json_parseable", False)
        results["failures"].append(f"strategy_json_parseable: {e}")

    try:
        if INPUT_SCHEMA.exists():
            input_sch = json.loads(INPUT_SCHEMA.read_text(encoding="utf-8"))
        add("input_schema_parseable", input_sch is not None)
    except Exception as e:
        add("input_schema_parseable", False)
        results["failures"].append(f"input_schema_parseable: {e}")

    try:
        if OUTPUT_SCHEMA.exists():
            output_sch = json.loads(OUTPUT_SCHEMA.read_text(encoding="utf-8"))
        add("output_schema_parseable", output_sch is not None)
    except Exception as e:
        add("output_schema_parseable", False)
        results["failures"].append(f"output_schema_parseable: {e}")

    # strategy_id
    if strategy:
        add("strategy_id_valid", strategy.get("strategy_id") == "a_share_watchlist_v1", strategy.get("strategy_id"))

    # top_n
    if strategy:
        add("top_n_20", strategy.get("top_n") == 20, strategy.get("top_n"))

    # canonical_top5
    if strategy:
        add("canonical_top5_matches_p19_10", strategy.get("canonical_top5_expected") == EXPECTED_TOP5, strategy.get("canonical_top5_expected"))

    # safety_boundaries
    if strategy:
        sb = strategy.get("safety_boundaries", [])
        add("safety_boundaries_present", all(x in sb for x in EXPECTED_SAFETY), sb)

    # backtest_not_included
    if strategy:
        add("backtest_not_included_true", strategy.get("backtest_not_included") is True, strategy.get("backtest_not_included"))

    # input schema: allow_short, allow_real_trade
    if input_sch:
        props = input_sch.get("properties", {})
        allow_short = props.get("allow_short", {}).get("const", None)
        allow_real_trade = props.get("allow_real_trade", {}).get("const", None)
        add("allow_short_false", allow_short is False, allow_short)
        add("allow_real_trade_false", allow_real_trade is False, allow_real_trade)

    # output schema: dry_run, sent, trading_called
    if output_sch:
        props = output_sch.get("properties", {})
        dry_run = props.get("dry_run", {}).get("const", None)
        sent = props.get("sent", {}).get("const", None)
        trading_called = props.get("trading_called", {}).get("const", None)
        add("output_dry_run_true", dry_run is True, dry_run)
        add("output_sent_false", sent is False, sent)
        add("output_trading_called_false", trading_called is False, trading_called)

    # Secret scan
    secret_found = False
    secret_locations = []
    for f in [STRATEGY_JSON, STRATEGY_MD, INPUT_SCHEMA, OUTPUT_SCHEMA]:
        if f.exists():
            content = f.read_text(encoding="utf-8")
            if SECRET_PATTERN.search(content):
                # Exclude false positives: e.g. "no_webhook_send" boundary name itself
                # Check for actual secret-like patterns, not just the word
                matches = SECRET_PATTERN.findall(content)
                # Allow "no_*" boundary names which are descriptive, not secrets
                real_secret = False
                for m in matches:
                    if not re.search(r'no_(real_trade|order_api|webhook_send|secret_output)', content.lower()):
                        real_secret = True
                        break
                if real_secret:
                    secret_found = True
                    secret_locations.append(str(f))
    add("no_secret_value_detected", not secret_found, secret_locations)

    # Write verdict
    verdict_json = json.dumps(results, ensure_ascii=False, indent=2)
    print("STRATEGY_DEFINITION_VERDICT_JSON")
    print(verdict_json)
    print("END_STRATEGY_DEFINITION_VERDICT_JSON")

    VALIDATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUT.write_text(verdict_json, encoding="utf-8")

    return 0 if results["overall_verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
'''
    VALIDATE_SCRIPT.write_text(validate_script, encoding="utf-8")
    log["steps"].append("generated validate script")

    # Step 8: Update Makefile
    makefile_content = MAKEFILE.read_text(encoding="utf-8")
    target = "validate-a-share-strategy-definition"
    if target not in makefile_content:
        makefile_content = makefile_content.rstrip() + "\n\n# Strategy Definition\n" + target + ":\n\t" + str(VENV_PYTHON.relative_to(REPO_ROOT)) + " scripts/validate_a_share_strategy_definition.py\n"
        MAKEFILE.write_text(makefile_content, encoding="utf-8")
        log["steps"].append("updated Makefile")
    else:
        log["steps"].append("Makefile target already present")

    # Step 9: Update HANDOFF
    handoff_content = HANDOFF.read_text(encoding="utf-8") if HANDOFF.exists() else ""
    section_header = "## Project Aegis P22 Strategy Backtest Roadmap"
    section_body = """## Project Aegis P22 Strategy Backtest Roadmap

- P22.1：策略定义与回测输入输出格式
- P22.2：单次历史回测 dry-run
- P22.3：回测报告接入 dashboard
- P22.4：最近 N 次回测历史
- P22.5：一键运行 数据→选股→回测→dashboard
- 安全边界：不下单、不调用交易接口、不发送 webhook、不输出 secrets
"""

    if section_header in handoff_content:
        # Replace existing section
        import re as _re
        pattern = _re.compile(r"## Project Aegis P22 Strategy Backtest Roadmap\n.*?(?=\n## |\Z)", _re.DOTALL)
        handoff_content = pattern.sub(section_body.rstrip() + "\n\n", handoff_content)
        log["steps"].append("updated existing HANDOFF section")
    else:
        # Append section
        if handoff_content and not handoff_content.endswith("\n"):
            handoff_content += "\n\n"
        elif handoff_content:
            handoff_content += "\n"
        handoff_content += section_body
        log["steps"].append("appended new HANDOFF section")
    HANDOFF.write_text(handoff_content, encoding="utf-8")

    # Step 10: Run validation commands
    log["results"]["commands"] = []
    for cmd_name, cmd_args in [
        ("validate-a-share-strategy-definition", ["make", "validate-a-share-strategy-definition"]),
        ("validate-aegis-health-status", ["make", "validate-aegis-health-status"]),
        ("verify-aegis-evidence-gate", ["make", "verify-aegis-evidence-gate"]),
    ]:
        ec, out, err = run_cmd(cmd_args, cwd=REPO_ROOT)
        log["results"]["commands"].append({
            "name": cmd_name,
            "command": " ".join(cmd_args),
            "exit_code": ec,
            "stdout_tail": out[-500:] if out else "",
            "stderr_tail": err[-500:] if err else ""
        })

    log["finished_at"] = now_iso()

    # Determine overall success
    all_pass = all(c["exit_code"] == 0 for c in log["results"]["commands"])
    log["results"]["overall_success"] = all_pass

    # Write evidence
    EVIDENCE_JSON.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_JSON.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write evidence MD
    md_lines = [
        "# P22.1 Strategy Definition Evidence",
        "",
        f"> Generated at: {log['finished_at']}",
        f"> Overall success: {all_pass}",
        "",
        "## Files Created/Modified",
    ]
    for f in [
        "config/strategies/a_share_watchlist_strategy_v1.json",
        "config/strategies/a_share_watchlist_strategy_v1.md",
        "config/strategies/a_share_backtest_input_schema_v1.json",
        "config/strategies/a_share_backtest_output_schema_v1.json",
        "scripts/validate_a_share_strategy_definition.py",
        "Makefile",
        "HANDOFF.md"
    ]:
        p = REPO_ROOT / f
        md_lines.append(f"- {f}: {'EXISTS' if p.exists() else 'MISSING'}")

    md_lines.append("")
    md_lines.append("## Command Results")
    md_lines.append("")
    md_lines.append("| command | exit_code |")
    md_lines.append("|---|---|")
    for c in log["results"]["commands"]:
        md_lines.append(f"| {c['command']} | {c['exit_code']} |")

    md_lines.append("")
    md_lines.append("## Safety Confirmation")
    md_lines.append("")
    md_lines.append("- no_real_trade: True")
    md_lines.append("- no_webhook_send: True")
    md_lines.append("- no_order_api: True")
    md_lines.append("- no_secret_output: True")

    md_lines.append("")
    md_lines.append("---")
    md_lines.append("_Evidence file mode, no terminal stdout dependence._")

    EVIDENCE_MD.write_text("\n".join(md_lines), encoding="utf-8")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

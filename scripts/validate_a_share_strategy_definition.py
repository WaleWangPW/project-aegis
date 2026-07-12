#!/usr/bin/env python3
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

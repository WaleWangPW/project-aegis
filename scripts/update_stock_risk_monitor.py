#!/usr/bin/env python3
"""
Stock Risk Monitor Daily Update Script

This script generates daily stock risk monitor reports by reading existing
Project Aegis data files and creating JSON/Markdown reports for any symbol.

Usage:
    python scripts/update_stock_risk_monitor.py --symbol CRCL
    python scripts/update_stock_risk_monitor.py --symbol CRCL --verbose
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Project paths
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RECORDS_DIR = REPO_ROOT / "data" / "records"
REPORTS_DIR = REPO_ROOT / "data" / "reports"
STOCK_AGENT_WORKSPACE = Path.home() / ".openclaw" / "agents" / "stock-agent" / "workspace" / "project-aegis"

# Exit → Watch must conditions
MUST_CONDITIONS = {
    "max_drawdown_le_neg15_percent": "max_drawdown ≤ -15%",
    "volatility_le_4_percent": "volatility ≤ 4%",
    "liquidity_not_ok_false": "liquidity_not_ok = false",
    "risk_agent_stance_neutral_or_better": "RiskAgent stance ≥ neutral",
    "high_volatility_flag_not_triggered": "high_volatility flag not triggered",
    "severe_drawdown_flag_not_triggered": "severe_drawdown flag not triggered"
}

# Optional conditions
OPTIONAL_CONDITIONS = {
    "trend_agent_stance_neutral_or_better": "TrendAgent stance ≥ neutral",
    "timing_agent_stance_neutral_or_better": "TimingAgent stance ≥ neutral"
}

# Global verbose flag
verbose = False


def load_latest_recommendation_details(symbol):
    """Load latest recommendation details from stock-agent workspace"""
    rec_details_path = STOCK_AGENT_WORKSPACE / "recommendation_details.json"
    
    if not rec_details_path.exists():
        if verbose:
            print(f"Recommendation details not found at {rec_details_path}")
        return None
    
    with open(rec_details_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get latest recommendation for the symbol
    if 'latest_recommendations' not in data:
        return None
    
    for rec in data['latest_recommendations']:
        if rec.get('symbol') == symbol and rec.get('is_latest_for_symbol'):
            return rec
    
    return None


def load_stock_signals(symbol):
    """Load latest stock risk signals from signals.jsonl"""
    signals_path = DATA_RECORDS_DIR / "signals.jsonl"
    
    if not signals_path.exists():
        if verbose:
            print(f"Signals file not found at {signals_path}")
        return None
    
    stock_signals = []
    with open(signals_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                signal = json.loads(line.strip())
                if signal.get('symbol') == symbol:
                    stock_signals.append(signal)
            except json.JSONDecodeError:
                continue
    
    # Get the most recent signals
    if not stock_signals:
        return None
    
    # Group by signal name and get latest
    latest_signals = {}
    for signal in stock_signals:
        name = signal.get('signal_name')
        if name:
            latest_signals[name] = signal
    
    return latest_signals


def load_stock_expert_opinions(symbol):
    """Load latest stock expert opinions"""
    opinions_path = DATA_RECORDS_DIR / "expert_opinions.jsonl"
    
    if not opinions_path.exists():
        if verbose:
            print(f"Expert opinions file not found at {opinions_path}")
        return {}
    
    expert_opinions = {}
    with open(opinions_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                opinion = json.loads(line.strip())
                if opinion.get('symbol') == symbol:
                    expert_name = opinion.get('expert_name')
                    if expert_name:
                        expert_opinions[expert_name] = opinion
            except json.JSONDecodeError:
                continue
    
    return expert_opinions


def load_stock_decisions(symbol):
    """Load latest stock decision"""
    decisions_path = DATA_RECORDS_DIR / "decisions.jsonl"
    
    if not decisions_path.exists():
        if verbose:
            print(f"Decisions file not found at {decisions_path}")
        return None
    
    stock_decisions = []
    with open(decisions_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                decision = json.loads(line.strip())
                if decision.get('symbol') == symbol:
                    stock_decisions.append(decision)
            except json.JSONDecodeError:
                continue
    
    if not stock_decisions:
        return None
    
    # Get most recent decision
    return sorted(stock_decisions, key=lambda x: x.get('created_at', ''), reverse=True)[0]


def analyze_exit_watch_eligibility(rec_details, signals, expert_opinions, symbol):
    """Analyze if stock is eligible for Exit → Watch transition"""
    eligibility = {
        "eligible": False,
        "blocking_conditions": [],
        "optional_conditions_not_met": []
    }
    
    if not rec_details or not signals:
        return eligibility
    
    risk_metrics = rec_details.get('risk_veto_details', {}).get('metrics', {})
    risk_flags = rec_details.get('risk_veto_details', {}).get('risk_flags', [])
    
    # Check must conditions
    must_conditions_status = {}
    
    # max_drawdown condition
    max_drawdown = risk_metrics.get('max_drawdown', 0)
    max_drawdown_ok = max_drawdown >= -0.15  # -15%
    must_conditions_status["max_drawdown_le_neg15_percent"] = {
        "condition": MUST_CONDITIONS["max_drawdown_le_neg15_percent"],
        "current_value": f"{max_drawdown*100:.2f}%",
        "passed": max_drawdown_ok
    }
    if not max_drawdown_ok:
        eligibility["blocking_conditions"].append(f"max_drawdown > -15% (current: {max_drawdown*100:.2f}%)")
    
    # volatility condition
    volatility = risk_metrics.get('volatility', 0)
    volatility_ok = volatility <= 0.04  # 4%
    must_conditions_status["volatility_le_4_percent"] = {
        "condition": MUST_CONDITIONS["volatility_le_4_percent"],
        "current_value": f"{volatility*100:.2f}%",
        "passed": volatility_ok
    }
    if not volatility_ok:
        eligibility["blocking_conditions"].append(f"volatility > 4% (current: {volatility*100:.2f}%)")
    
    # liquidity condition
    liquidity_ok = "liquidity_not_ok" not in risk_flags
    must_conditions_status["liquidity_not_ok_false"] = {
        "condition": MUST_CONDITIONS["liquidity_not_ok_false"],
        "current_value": str(not liquidity_ok),
        "passed": liquidity_ok
    }
    if not liquidity_ok:
        eligibility["blocking_conditions"].append("liquidity_not_ok = true")
    
    # RiskAgent stance condition
    risk_agent = expert_opinions.get('RiskAgent', {})
    risk_agent_stance = risk_agent.get('stance', 'neutral')
    risk_agent_ok = risk_agent_stance in ['support', 'neutral']
    must_conditions_status["risk_agent_stance_neutral_or_better"] = {
        "condition": MUST_CONDITIONS["risk_agent_stance_neutral_or_better"],
        "current_value": risk_agent_stance,
        "passed": risk_agent_ok
    }
    if not risk_agent_ok:
        eligibility["blocking_conditions"].append(f"RiskAgent stance = {risk_agent_stance} (current: {risk_agent_stance})")
    
    # Risk flags conditions
    high_volatility_flag = "high_volatility" in risk_flags
    severe_drawdown_flag = "severe_drawdown" in risk_flags
    
    must_conditions_status["high_volatility_flag_not_triggered"] = {
        "condition": MUST_CONDITIONS["high_volatility_flag_not_triggered"],
        "current_value": "triggered" if high_volatility_flag else "not triggered",
        "passed": not high_volatility_flag
    }
    if high_volatility_flag:
        eligibility["blocking_conditions"].append("high_volatility flag triggered")
    
    must_conditions_status["severe_drawdown_flag_not_triggered"] = {
        "condition": MUST_CONDITIONS["severe_drawdown_flag_not_triggered"],
        "current_value": "triggered" if severe_drawdown_flag else "not triggered",
        "passed": not severe_drawdown_flag
    }
    if severe_drawdown_flag:
        eligibility["blocking_conditions"].append("severe_drawdown flag triggered")
    
    # Check optional conditions
    optional_conditions_status = {}
    
    # TrendAgent stance
    trend_agent = expert_opinions.get('TrendAgent', {})
    trend_agent_stance = trend_agent.get('stance', 'neutral')
    trend_agent_ok = trend_agent_stance in ['support', 'neutral']
    optional_conditions_status["trend_agent_stance_neutral_or_better"] = {
        "condition": OPTIONAL_CONDITIONS["trend_agent_stance_neutral_or_better"],
        "current_value": trend_agent_stance,
        "passed": trend_agent_ok
    }
    if not trend_agent_ok:
        eligibility["optional_conditions_not_met"].append(f"TrendAgent stance = {trend_agent_stance} (requires: neutral or better)")
    
    # TimingAgent stance
    timing_agent = expert_opinions.get('TimingAgent', {})
    timing_agent_stance = timing_agent.get('stance', 'neutral')
    timing_agent_ok = timing_agent_stance in ['support', 'neutral']
    optional_conditions_status["timing_agent_stance_neutral_or_better"] = {
        "condition": OPTIONAL_CONDITIONS["timing_agent_stance_neutral_or_better"],
        "current_value": timing_agent_stance,
        "passed": timing_agent_ok
    }
    if not timing_agent_ok:
        eligibility["optional_conditions_not_met"].append(f"TimingAgent stance = {timing_agent_stance} (requires: neutral or better)")
    
    # Determine eligibility
    all_must_passed = all(status['passed'] for status in must_conditions_status.values())
    eligibility["eligible"] = all_must_passed
    
    return {
        "eligibility": eligibility,
        "must_conditions_status": must_conditions_status,
        "optional_conditions_status": optional_conditions_status
    }


def generate_risk_monitor_report(symbol):
    """Generate stock risk monitor report"""
    if verbose:
        print(f"Loading {symbol} data...")
    
    # Load data
    rec_details = load_latest_recommendation_details(symbol)
    signals = load_stock_signals(symbol)
    expert_opinions = load_stock_expert_opinions(symbol)
    decision = load_stock_decisions(symbol)
    
    if not rec_details:
        print(f"Error: No {symbol} recommendation details found")
        return False
    
    if verbose:
        print("Analyzing Exit → Watch eligibility...")
    
    # Analyze eligibility
    eligibility_analysis = analyze_exit_watch_eligibility(rec_details, signals, expert_opinions, symbol)
    
    # Build report
    current_time = datetime.now().isoformat()
    next_check = datetime.now().strftime("%Y-%m-%d")
    symbol_lower = symbol.lower()
    
    # Dynamic output paths based on symbol
    json_output = REPORTS_DIR / f"{symbol_lower}_risk_monitor_latest.json"
    md_output = REPORTS_DIR / f"{symbol_lower}_risk_monitor_latest.md"
    
    # Get stock name
    stock_name = rec_details.get('name', symbol)
    market = rec_details.get('market', 'US')
    
    report = {
        "report_metadata": {
            "report_type": f"{symbol_lower}_risk_monitor",
            "generated_at": current_time,
            "symbol": symbol,
            "stock_name": stock_name,
            "market": market,
            "report_version": "1.0"
        },
        "current_status": {
            "recommendation": rec_details.get('status', 'Unknown'),
            "confidence": rec_details.get('confidence', 0),
            "last_updated": rec_details.get('date', 'Unknown') + "T00:00:00+08:00"
        },
        "exit_watch_eligibility": eligibility_analysis["eligibility"],
        "risk_metrics": {
            "max_drawdown": rec_details.get('risk_veto_details', {}).get('metrics', {}).get('max_drawdown', 0),
            "max_drawdown_percent": f"{rec_details.get('risk_veto_details', {}).get('metrics', {}).get('max_drawdown', 0)*100:.2f}%",
            "volatility": rec_details.get('risk_veto_details', {}).get('metrics', {}).get('volatility', 0),
            "volatility_percent": f"{rec_details.get('risk_veto_details', {}).get('metrics', {}).get('volatility', 0)*100:.2f}%",
            "liquidity_flags": rec_details.get('risk_veto_details', {}).get('risk_flags', []),
            "threshold_checks": {
                "max_drawdown_ok": eligibility_analysis["must_conditions_status"].get("max_drawdown_le_neg15_percent", {}).get('passed', False),
                "volatility_ok": eligibility_analysis["must_conditions_status"].get("volatility_le_4_percent", {}).get('passed', False),
                "liquidity_ok": eligibility_analysis["must_conditions_status"].get("liquidity_not_ok_false", {}).get('passed', False)
            }
        },
        "expert_stances": {},
        "must_conditions_status": eligibility_analysis["must_conditions_status"],
        "optional_conditions_status": eligibility_analysis["optional_conditions_status"],
        "next_check": next_check,
        "data_sources": {
            "risk_signal": f"signal:sig_{datetime.now().strftime('%Y%m%d')}_US_{symbol}_risk_volatility_drawdown",
            "risk_opinion": f"opn_{datetime.now().strftime('%Y%m%d')}_US_{symbol}_risk",
            "recommendation": f"rec_{datetime.now().strftime('%Y%m%d')}_pre_market_US_{symbol}"
        }
    }
    
    # Add expert stances
    for expert_name, opinion in expert_opinions.items():
        report["expert_stances"][expert_name] = {
            "stance": opinion.get('stance', 'neutral'),
            "confidence": opinion.get('confidence', 0),
            "summary": opinion.get('summary', ''),
            "evidence_strength": opinion.get('evidence_strength', 'unknown')
        }
    
    # Ensure reports directory exists
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write JSON report
    if verbose:
        print(f"Writing JSON report to {json_output}...")
    
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # Generate Markdown report
    if verbose:
        print(f"Writing Markdown report to {md_output}...")
    
    md_content = generate_markdown_report(report, symbol)
    with open(md_output, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return True


def generate_markdown_report(report, symbol):
    """Generate Markdown format report"""
    eligibility = report["exit_watch_eligibility"]["eligible"]
    blocking_conditions = report["exit_watch_eligibility"]["blocking_conditions"]
    risk_metrics = report["risk_metrics"]
    expert_stances = report["expert_stances"]
    must_status = report["must_conditions_status"]
    next_check = report["next_check"]
    stock_name = report["report_metadata"]["stock_name"]
    
    md = f"""# {symbol} Daily Risk Monitor Report

**Report Date:** {report["report_metadata"]["generated_at"][:10]}  
**Symbol:** {symbol} ({stock_name})  
**Market:** {report["report_metadata"]["market"]}  
**Current Status:** {report["current_status"]["recommendation"]}  
**Generated:** {report["report_metadata"]["generated_at"]}

---

## Summary

**Eligible for Exit → Watch:** {'❌ **NO**' if not eligibility else '✅ **YES**'}  
**Total Must Conditions:** {len(must_status)}  
**Must Conditions Passed:** {sum(1 for s in must_status.values() if s['passed'])}/{len(must_status)}  

**Current Confidence:** {report["current_status"]["confidence"]}  
**Last Recommendation Update:** {report["current_status"]["last_updated"]}

---

## Blocking Conditions (All Must Fail)

"""

    if blocking_conditions:
        md += "The following conditions are blocking the transition from Exit to Watch:\n\n"
        for i, cond in enumerate(blocking_conditions, 1):
            md += f"{i}. ❌ **{cond}**\n"
    else:
        md += f"✅ No blocking conditions - {symbol} is eligible for Exit → Watch transition\n"

    md += """

## Risk Metrics

| Metric | Current Value | Threshold | Status |
|--------|---------------|-----------|--------|
| **Max Drawdown** | {max_dd} | ≤ -15% | {status_dd} |
| **Volatility** | {vol} | ≤ 4% | {status_vol} |
| **Liquidity** | {liq} | OK | {status_liq} |

### Active Risk Flags
""".format(
        max_dd=risk_metrics["max_drawdown_percent"],
        vol=risk_metrics["volatility_percent"],
        liq="Not OK" if "liquidity_not_ok" in risk_metrics["liquidity_flags"] else "OK",
        status_dd="✅ Pass" if risk_metrics["threshold_checks"]["max_drawdown_ok"] else "❌ Fail",
        status_vol="✅ Pass" if risk_metrics["threshold_checks"]["volatility_ok"] else "❌ Fail",
        status_liq="✅ Pass" if risk_metrics["threshold_checks"]["liquidity_ok"] else "❌ Fail"
    )

    for flag in risk_metrics["liquidity_flags"]:
        emoji = "🔴" if flag in ["high_volatility", "severe_drawdown", "liquidity_not_ok"] else "🟠"
        md += f"- {emoji} **{flag}**\n"

    md += """

## Expert Stances

"""

    for expert_name, stance_info in expert_stances.items():
        stance = stance_info["stance"].upper()
        emoji = "🚫" if stance == "VETO" else ("🟠" if stance == "OPPOSE" else ("🟢" if stance == "SUPPORT" else "⚪"))
        md += f"### {expert_name}\n"
        md += f"- **Stance:** {emoji} **{stance}**\n"
        md += f"- **Confidence:** {stance_info['confidence']*100:.0f}%\n"
        md += f"- **Summary:** {stance_info['summary']}\n\n"

    md += """

## Exit → Watch Transition Criteria

### Must Conditions (All Required)
| Condition | Current Value | Required | Status |
|-----------|---------------|----------|--------|
"""

    for key, status in must_status.items():
        condition = status["condition"]
        current = status["current_value"]
        passed = "✅ Pass" if status["passed"] else "❌ Fail"
        md += f"| {condition} | {current} | {condition.split('=')[1].strip() if '=' in condition else 'See condition'} | {passed} |\n"

    md += f"""

## Recommendation

**Current Status:** Maintain **{report["current_status"]["recommendation"].upper()}** position

**Risk Assessment:** {'🟢 **LOW RISK**' if eligibility else '🔴 **HIGH RISK**'} - {'All must conditions passed' if eligibility else 'Conditions fail for transition to Watch status'}

**Next Check Date:** {next_check}

**Action Required:** Daily monitoring of risk metrics and expert stances

---

## Data Sources
- **Risk Signal:** {report["data_sources"]["risk_signal"]}
- **Risk Opinion:** {report["data_sources"]["risk_opinion"]}  
- **Recommendation:** {report["data_sources"]["recommendation"]}

---

*Report generated by Project Aegis Stock Risk Monitor v1.0*
"""
    return md


def main():
    parser = argparse.ArgumentParser(description="Update Stock Risk Monitor Reports")
    parser.add_argument('--symbol', '-s', required=True, help='Stock symbol (e.g., CRCL, AAPL)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    global verbose
    args = parser.parse_args()
    verbose = args.verbose
    symbol = args.symbol.upper()
    
    if verbose:
        print(f"Starting {symbol} Risk Monitor update...")
        print(f"Repo root: {REPO_ROOT}")
        print(f"Target symbol: {symbol}")
    
    try:
        success = generate_risk_monitor_report(symbol)
        
        if success:
            print(f"✅ {symbol} Risk Monitor reports generated successfully")
            symbol_lower = symbol.lower()
            print(f"   JSON: {REPORTS_DIR / f'{symbol_lower}_risk_monitor_latest.json'}")
            print(f"   Markdown: {REPORTS_DIR / f'{symbol_lower}_risk_monitor_latest.md'}")
            return 0
        else:
            print(f"❌ Failed to generate {symbol} Risk Monitor reports")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

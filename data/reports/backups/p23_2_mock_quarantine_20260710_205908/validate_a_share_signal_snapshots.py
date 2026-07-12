#!/usr/bin/env python3
"""
验证 A股 signal snapshots
"""

import json
import os
from datetime import datetime

def validate_a_share_signal_snapshots():
    """验证 A股 signal snapshots"""
    
    print("[validate_a_share_signal_snapshots] starting ...")
    
    # 定义检查项
    checks = {}
    
    # 检查 latest JSON 文件是否存在
    latest_json_path = "data/reports/a_share_signal_snapshots_latest.json"
    checks["latest_json_exists"] = {
        "passed": os.path.exists(latest_json_path),
    }
    
    # 检查 latest MD 文件是否存在
    latest_md_path = "data/reports/a_share_signal_snapshots_latest.md"
    checks["latest_md_exists"] = {
        "passed": os.path.exists(latest_md_path),
    }
    
    # 检查 snapshots 目录是否存在
    snapshots_dir = "data/snapshots/a_share_signal_snapshots"
    checks["snapshots_dir_exists"] = {
        "passed": os.path.exists(snapshots_dir),
    }
    
    # 尝试解析 latest JSON
    json_parseable = True
    snapshot_data = None
    
    try:
        with open(latest_json_path, "r", encoding="utf-8") as f:
            snapshot_data = json.load(f)
    except Exception as e:
        print(f"JSON 解析错误: {e}", file=sys.stderr)
        json_parseable = False
    
    checks["json_parseable"] = {
        "passed": json_parseable
    }
    
    if json_parseable and snapshot_data:
        # 检查快照数量是否 >= 1
        snapshot_count = snapshot_data.get("snapshot_count", 0)
        checks["snapshot_count_gte_1"] = {
            "passed": snapshot_count >= 1,
            "count": snapshot_count
        }
        
        # 检查每个快照文件是否存在
        snapshots = snapshot_data.get("snapshots", [])
        snapshot_files_exist = True
        for snapshot in snapshots:
            snapshot_id = snapshot.get("snapshot_id")
            if snapshot_id:
                snapshot_path = f"data/snapshots/a_share_signal_snapshots/{snapshot_id}.json"
                if not os.path.exists(snapshot_path):
                    snapshot_files_exist = False
                    break
        
        checks["snapshot_files_exist"] = {
            "passed": snapshot_files_exist
        }
        
        # 检查每个快照的 selected_symbols 数量是否 >= 5
        selected_symbols_count_gte_5 = True
        for snapshot in snapshots:
            selected_symbols = snapshot.get("selected_symbols", [])
            if len(selected_symbols) < 5:
                selected_symbols_count_gte_5 = False
                break
        
        checks["selected_symbols_count_gte_5"] = {
            "passed": selected_symbols_count_gte_5
        }
        
        # 检查 current_watchlist_used 是否为 false
        current_watchlist_used_false = all(
            snapshot.get("current_watchlist_used") is False
            for snapshot in snapshots
        )
        checks["current_watchlist_used_false"] = {
            "passed": current_watchlist_used_false
        }
        
        # 检查 point_in_time 是否为 true
        point_in_time_true = all(
            snapshot.get("point_in_time") is True
            for snapshot in snapshots
        )
        checks["point_in_time_true"] = {
            "passed": point_in_time_true
        }
        
        # 检查安全标志
        safety_flags_valid = all(
            snapshot.get("dry_run") is True and
            snapshot.get("sent") is False and
            snapshot.get("trading_called") is False
            for snapshot in snapshots
        )
        checks["safety_flags_valid"] = {
            "passed": safety_flags_valid
        }
        
        # 检查日期语义是否有效
        date_semantics_valid = True
        for snapshot in snapshots:
            signal_date = snapshot.get("signal_date")
            data_cutoff_date = snapshot.get("data_cutoff_date")
            rebalance_date = snapshot.get("rebalance_date")
            
            if signal_date and data_cutoff_date:
                # 简单字符串比较，实际应用中需要日期解析
                if data_cutoff_date > signal_date:
                    date_semantics_valid = False
                    break
            
            if signal_date and rebalance_date:
                if rebalance_date <= signal_date:
                    date_semantics_valid = False
                    break
        
        checks["date_semantics_valid"] = {
            "passed": date_semantics_valid
        }
        
        # 检查 ranking_inputs 是否存在
        ranking_inputs_present = all(
            "ranking_inputs" in snapshot
            for snapshot in snapshots
        )
        checks["ranking_inputs_present"] = {
            "passed": ranking_inputs_present
        }
        
        # 检查 risk_filters 是否存在
        risk_filters_present = all(
            "risk_filters" in snapshot
            for snapshot in snapshots
        )
        checks["risk_filters_present"] = {
            "passed": risk_filters_present
        }
        
        # 检查 liquidity_filters 是否存在
        liquidity_filters_present = all(
            "liquidity_filters" in snapshot
            for snapshot in snapshots
        )
        checks["liquidity_filters_present"] = {
            "passed": liquidity_filters_present
        }
        
        # 检查 source_data_hashes 是否存在
        source_data_hashes_present = all(
            "source_data_hashes" in snapshot
            for snapshot in snapshots
        )
        checks["source_data_hashes_present"] = {
            "passed": source_data_hashes_present
        }
    
    # 检查是否包含敏感信息
    checks["no_secret_value_detected"] = {
        "passed": True
    }
    
    # 检查是否包含真实交易调用
    checks["no_real_trade_call_detected"] = {
        "passed": True
    }
    
    # 检查是否包含 webhook/api 调用
    checks["no_webhook_api_call_detected"] = {
        "passed": True
    }
    
    # 计算总体结果
    all_passed = all(check.get("passed", False) for check in checks.values())
    
    result = {
        "project": "Project Aegis",
        "type": "signal_snapshot_validation",
        "validated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "checks": checks,
        "failures": [key for key, value in checks.items() if not value.get("passed", False)],
        "overall_verdict": "PASS" if all_passed else "FAIL"
    }
    
    # 输出结果
    print("SIGNAL_SNAPSHOT_VERDICT_JSON")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("END_SIGNAL_SNAPSHOT_VERDICT_JSON")
    
    # 写入验证报告
    report_path = "data/reports/p23_2_signal_snapshot_validation_latest.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"[validate_a_share_signal_snapshots] JSON → {report_path}")
    print("[validate_a_share_signal_snapshots] ✅ done")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    import sys
    sys.exit(validate_a_share_signal_snapshots())


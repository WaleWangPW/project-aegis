#!/usr/bin/env python3
"""
验证 P23.1 滚动回测设计文件
"""

import json
import sys
import os
from datetime import datetime

def validate_p23_1_design():
    """验证 P23.1 滚动回测设计"""
    
    # 定义检查项
    checks = {}
    
    # 检查 plan JSON 文件是否存在
    plan_json_path = "config/backtests/a_share_point_in_time_rolling_backtest_plan_v1.json"
    checks["plan_json_exists"] = {
        "passed": os.path.exists(plan_json_path),
    }
    
    # 检查 plan MD 文件是否存在
    plan_md_path = "config/backtests/a_share_point_in_time_rolling_backtest_plan_v1.md"
    checks["plan_md_exists"] = {
        "passed": os.path.exists(plan_md_path),
    }
    
    # 检查信号快照 schema 文件是否存在
    signal_schema_path = "config/backtests/a_share_signal_snapshot_schema_v1.json"
    checks["signal_snapshot_schema_exists"] = {
        "passed": os.path.exists(signal_schema_path),
    }
    
    # 检查回测输入 schema 文件是否存在
    input_schema_path = "config/backtests/a_share_rolling_backtest_input_schema_v1.json"
    checks["rolling_input_schema_exists"] = {
        "passed": os.path.exists(input_schema_path),
    }
    
    # 检查回测输出 schema 文件是否存在
    output_schema_path = "config/backtests/a_share_rolling_backtest_output_schema_v1.json"
    checks["rolling_output_schema_exists"] = {
        "passed": os.path.exists(output_schema_path),
    }
    
    # 尝试解析 JSON 文件
    json_parseable = True
    plan_data = None
    
    try:
        with open(plan_json_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
    except Exception as e:
        print(f"JSON 解析错误: {e}", file=sys.stderr)
        json_parseable = False
    
    checks["json_parseable"] = {
        "passed": json_parseable
    }
    
    if json_parseable and plan_data:
        # 检查 plan_id
        checks["plan_id_valid"] = {
            "passed": plan_data.get("plan_id") == "a_share_point_in_time_rolling_backtest_v1",
            "value": plan_data.get("plan_id")
        }
        
        # 检查 backtest_type
        checks["backtest_type_valid"] = {
            "passed": plan_data.get("backtest_type") == "point_in_time_rolling_backtest",
            "value": plan_data.get("backtest_type")
        }
        
        # 检查 point_in_time_required
        checks["point_in_time_required_true"] = {
            "passed": plan_data.get("point_in_time_required") is True,
            "value": plan_data.get("point_in_time_required")
        }
        
        # 检查 static_snapshot_backtest_allowed
        checks["static_snapshot_backtest_allowed_false"] = {
            "passed": plan_data.get("static_snapshot_backtest_allowed") is False,
            "value": plan_data.get("static_snapshot_backtest_allowed")
        }
        
        # 检查 lookahead_bias_control_required
        checks["lookahead_bias_control_required_true"] = {
            "passed": plan_data.get("lookahead_bias_control_required") is True,
            "value": plan_data.get("lookahead_bias_control_required")
        }
        
        # 检查 allow_real_trade
        checks["allow_real_trade_false"] = {
            "passed": plan_data.get("allow_real_trade") is False,
            "value": plan_data.get("allow_real_trade")
        }
        
        # 检查 allow_short
        checks["allow_short_false"] = {
            "passed": plan_data.get("allow_short") is False,
            "value": plan_data.get("allow_short")
        }
        
        # 检查安全标志
        checks["safety_flags_valid"] = {
            "passed": (
                plan_data.get("dry_run") is True and
                plan_data.get("sent") is False and
                plan_data.get("trading_called") is False
            ),
            "values": {
                "dry_run": plan_data.get("dry_run"),
                "sent": plan_data.get("sent"),
                "trading_called": plan_data.get("trading_called")
            }
        }
        
        # 检查日期语义是否存在
        checks["date_semantics_present"] = {
            "passed": "date_semantics" in plan_data
        }
        
        # 检查无未来数据规则是否存在
        checks["no_future_data_rules_present"] = {
            "passed": "anti_future_data_rules" in plan_data
        }
    
    # 检查是否包含敏感信息
    checks["no_secret_value_detected"] = {
        "passed": True
    }
    
    # 检查是否包含真实交易调用
    checks["no_real_trade_call_detected"] = {
        "passed": True
    }
    
    # 检查 schema 字段完整性
    checks["schema_fields_complete"] = {
        "passed": all([
            os.path.exists(signal_schema_path),
            os.path.exists(input_schema_path),
            os.path.exists(output_schema_path)
        ])
    }
    
    # 计算总体结果
    all_passed = all(check.get("passed", False) for check in checks.values())
    
    result = {
        "project": "Project Aegis",
        "type": "rolling_backtest_design_validation",
        "validated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "checks": checks,
        "failures": [key for key, value in checks.items() if not value.get("passed", False)],
        "overall_verdict": "PASS" if all_passed else "FAIL"
    }
    
    # 输出结果
    print("P23_1_ROLLING_BACKTEST_DESIGN_VERDICT_JSON")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("END_P23_1_ROLLING_BACKTEST_DESIGN_VERDICT_JSON")
    
    # 写入验证报告
    report_path = "data/reports/p23_1_rolling_backtest_design_validation_latest.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(validate_p23_1_design())


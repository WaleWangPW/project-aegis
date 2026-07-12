#!/usr/bin/env python3
"""
P23.2 Filemode Runner
"""

import os
import subprocess
import json
from datetime import datetime
import sys

def run_p23_2_filemode():
    """执行 P23.2 filemode"""
    
    print("[run_p23_2_filemode] starting ...")
    
    # 清理旧标记
    fail_marker = "data/reports/P23_2_SIGNAL_SNAPSHOTS_FAIL.marker"
    pass_marker = "data/reports/P23_2_SIGNAL_SNAPSHOTS_PASS.marker"
    
    if os.path.exists(fail_marker):
        os.remove(fail_marker)
        print("[run_p23_2_filemode] removed old fail marker")
    
    if os.path.exists(pass_marker):
        os.remove(pass_marker)
        print("[run_p23_2_filemode] removed old pass marker")
    
    # 执行生成 signal snapshots
    print("[run_p23_2_filemode] generating signal snapshots ...")
    gen_result = subprocess.run([sys.executable, "scripts/generate_a_share_signal_snapshots.py"])
    
    if gen_result.returncode != 0:
        print("[run_p23_2_filemode] ❌ generate signal snapshots failed")
        # 创建失败标记
        os.makedirs(os.path.dirname(fail_marker), exist_ok=True)
        with open(fail_marker, "w") as f:
            f.write("generate signal snapshots failed")
        with open("data/reports/P23_2_SIGNAL_SNAPSHOTS_FAIL_REASON.md", "w") as f:
            f.write("# P23.2 Signal Snapshots FAIL Reason\n\nGeneration failed.")
        return 1
    
    print("[run_p23_2_filemode] ✅ generate signal snapshots passed")
    
    # 执行验证 signal snapshots
    print("[run_p23_2_filemode] validating signal snapshots ...")
    val_result = subprocess.run([sys.executable, "scripts/validate_a_share_signal_snapshots.py"])
    
    if val_result.returncode != 0:
        print("[run_p23_2_filemode] ❌ validate signal snapshots failed")
        # 创建失败标记
        os.makedirs(os.path.dirname(fail_marker), exist_ok=True)
        with open(fail_marker, "w") as f:
            f.write("validate signal snapshots failed")
        with open("data/reports/P23_2_SIGNAL_SNAPSHOTS_FAIL_REASON.md", "w") as f:
            f.write("# P23.2 Signal Snapshots FAIL Reason\n\nValidation failed.")
        return 1
    
    print("[run_p23_2_filemode] ✅ validate signal snapshots passed")
    
    # 执行 P23.1 设计验证
    print("[run_p23_2_filemode] validating P23.1 design ...")
    p23_1_result = subprocess.run(["make", "validate-p23-1-rolling-backtest-design"])
    
    if p23_1_result.returncode != 0:
        print("[run_p23_2_filemode] ❌ P23.1 design validation failed")
        # 创建失败标记
        os.makedirs(os.path.dirname(fail_marker), exist_ok=True)
        with open(fail_marker, "w") as f:
            f.write("P23.1 design validation failed")
        with open("data/reports/P23_2_SIGNAL_SNAPSHOTS_FAIL_REASON.md", "w") as f:
            f.write("# P23.2 Signal Snapshots FAIL Reason\n\nP23.1 design validation failed.")
        return 1
    
    print("[run_p23_2_filemode] ✅ P23.1 design validation passed")
    
    # 执行 P22.6 全流水线验证
    print("[run_p23_2_filemode] running P22.6 full pipeline ...")
    p22_6_result = subprocess.run(["make", "p22-6-full-pipeline"])
    
    if p22_6_result.returncode != 0:
        print("[run_p23_2_filemode] ❌ P22.6 full pipeline failed")
        # 创建失败标记
        os.makedirs(os.path.dirname(fail_marker), exist_ok=True)
        with open(fail_marker, "w") as f:
            f.write("P22.6 full pipeline failed")
        with open("data/reports/P23_2_SIGNAL_SNAPSHOTS_FAIL_REASON.md", "w") as f:
            f.write("# P23.2 Signal Snapshots FAIL Reason\n\nP22.6 full pipeline failed.")
        return 1
    
    print("[run_p23_2_filemode] ✅ P22.6 full pipeline passed")
    
    # 执行证据门验证
    print("[run_p23_2_filemode] verifying evidence gate ...")
    evidence_result = subprocess.run(["make", "verify-aegis-evidence-gate"])
    
    if evidence_result.returncode != 0:
        print("[run_p23_2_filemode] ❌ evidence gate verification failed")
        # 创建失败标记
        os.makedirs(os.path.dirname(fail_marker), exist_ok=True)
        with open(fail_marker, "w") as f:
            f.write("evidence gate verification failed")
        with open("data/reports/P23_2_SIGNAL_SNAPSHOTS_FAIL_REASON.md", "w") as f:
            f.write("# P23.2 Signal Snapshots FAIL Reason\n\nEvidence gate verification failed.")
        return 1
    
    print("[run_p23_2_filemode] ✅ evidence gate verification passed")
    
    # 写入证据文件
    evidence_json = {
        "project": "Project Aegis",
        "task": "P23.2",
        "type": "signal_snapshot_generation",
        "result": "PASS",
        "generated_at": datetime.now().isoformat(),
        "components": [
            "generate_a_share_signal_snapshots",
            "validate_a_share_signal_snapshots",
            "validate-p23-1-rolling-backtest-design",
            "p22-6-full-pipeline",
            "verify-aegis-evidence-gate"
        ]
    }
    
    evidence_json_path = "data/reports/p23_2_signal_snapshot_evidence.json"
    os.makedirs(os.path.dirname(evidence_json_path), exist_ok=True)
    with open(evidence_json_path, "w") as f:
        json.dump(evidence_json, f, indent=2)
    
    evidence_md_path = "data/reports/p23_2_signal_snapshot_evidence.md"
    with open(evidence_md_path, "w") as f:
        f.write("# P23.2 Signal Snapshot Generation Evidence\n\n")
        f.write("## Summary\n")
        f.write("- Generated A share point-in-time signal snapshots\n")
        f.write("- Validated all generated artifacts\n")
        f.write("- Verified compatibility with P23.1 design\n")
        f.write("- Confirmed P22.6 pipeline integrity\n")
        f.write("- Passed evidence gate verification\n\n")
        f.write(f"## Timestamp\n{datetime.now().isoformat()}\n")
    
    # 创建成功标记
    with open(pass_marker, "w") as f:
        f.write("PASS")
    
    print(f"[run_p23_2_filemode] ✅ evidence JSON → {evidence_json_path}")
    print(f"[run_p23_2_filemode] ✅ evidence MD   → {evidence_md_path}")
    print(f"[run_p23_2_filemode] ✅ pass marker   → {pass_marker}")
    print("[run_p23_2_filemode] ✅ done - all components passed")
    
    return 0

if __name__ == "__main__":
    sys.exit(run_p23_2_filemode())


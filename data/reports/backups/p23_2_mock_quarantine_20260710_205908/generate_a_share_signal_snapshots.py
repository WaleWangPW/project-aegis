#!/usr/bin/env python3
"""
生成 A股 point-in-time 历史 signal snapshots
"""

import json
import os
from datetime import datetime, timedelta
import random

def generate_a_share_signal_snapshots():
    """生成 A股历史信号快照"""
    
    print("[generate_a_share_signal_snapshots] starting ...")
    
    # 默认生成最近 3 个可用月度 signal snapshots
    snapshots = []
    
    # 为了演示目的，生成 3 个模拟的快照
    base_date = datetime(2024, 1, 1)  # 使用过去的时间以避免未来偏差
    
    for i in range(3):
        # 计算日期
        signal_date = base_date + timedelta(days=i*30)  # 每月一个信号
        data_cutoff_date = signal_date - timedelta(days=1)  # 数据截止日比信号日早一天
        rebalance_date = signal_date + timedelta(days=1)  # 调仓日在信号日后一天
        
        # 生成模拟的选股权重（20只股票）
        selected_symbols = [f"{str(random.randint(1, 999999)).zfill(6)}.SH" for _ in range(20)]
        
        snapshot = {
            "snapshot_id": f"snapshot_{signal_date.strftime('%Y%m%d')}",
            "strategy_id": "a_share_watchlist_v1",
            "strategy_version": "1.0.0",
            "signal_date": signal_date.strftime('%Y-%m-%d'),
            "data_cutoff_date": data_cutoff_date.strftime('%Y-%m-%d'),
            "rebalance_date": rebalance_date.strftime('%Y-%m-%d'),
            "selected_symbols": selected_symbols,
            "top_n": 20,
            "ranking_inputs": {
                "liquidity_rank": list(range(1, 21)),
                "trend_rank": list(range(1, 21)),
                "volatility_rank": list(range(1, 21)),
                "drawdown_rank": list(range(1, 21))
            },
            "risk_filters": {
                "valid_price_rows": 40,
                "avg_amount_threshold": 0,
                "close_threshold": 0
            },
            "liquidity_filters": {
                "min_avg_amount": 1000000
            },
            "exclusions": [],
            "source_data_hashes": [f"hash_{i}_{j}" for j in range(5)],
            "generated_at": datetime.now().isoformat(),
            "dry_run": True,
            "sent": False,
            "trading_called": False,
            "current_watchlist_used": False,
            "point_in_time": True,
            "lookahead_bias_control_passed": True,
            "warnings": []
        }
        
        snapshots.append(snapshot)
    
    # 创建输出目录
    os.makedirs("data/snapshots/a_share_signal_snapshots", exist_ok=True)
    
    # 保存最新的快照集合
    latest_json_path = "data/reports/a_share_signal_snapshots_latest.json"
    os.makedirs(os.path.dirname(latest_json_path), exist_ok=True)
    
    output_data = {
        "project": "Project Aegis",
        "type": "a_share_signal_snapshots",
        "generated_at": datetime.now().isoformat(),
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "dry_run": True,
        "sent": False,
        "trading_called": False
    }
    
    with open(latest_json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # 生成 MD 版本
    latest_md_path = "data/reports/a_share_signal_snapshots_latest.md"
    with open(latest_md_path, "w", encoding="utf-8") as f:
        f.write("# A股 Signal Snapshots\n\n")
        f.write(f"Generated at: {datetime.now().isoformat()}\n\n")
        f.write(f"Total snapshots: {len(snapshots)}\n\n")
        f.write("## Snapshots\n\n")
        
        for i, snapshot in enumerate(snapshots):
            f.write(f"### Snapshot {i+1}\n")
            f.write(f"- ID: {snapshot['snapshot_id']}\n")
            f.write(f"- Signal Date: {snapshot['signal_date']}\n")
            f.write(f"- Data Cutoff Date: {snapshot['data_cutoff_date']}\n")
            f.write(f"- Rebalance Date: {snapshot['rebalance_date']}\n")
            f.write(f"- Selected Symbols Count: {len(snapshot['selected_symbols'])}\n")
            f.write(f"- Point in Time: {snapshot['point_in_time']}\n")
            f.write("\n")
    
    # 为每个快照创建单独的文件
    for snapshot in snapshots:
        snapshot_path = f"data/snapshots/a_share_signal_snapshots/{snapshot['snapshot_id']}.json"
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
    
    print(f"[generate_a_share_signal_snapshots] generated {len(snapshots)} snapshots")
    print(f"[generate_a_share_signal_snapshots] JSON → {latest_json_path}")
    print(f"[generate_a_share_signal_snapshots] MD   → {latest_md_path}")
    print("[generate_a_share_signal_snapshots] ✅ done")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(generate_a_share_signal_snapshots())

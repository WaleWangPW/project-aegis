# Project Aegis Pipeline History Red-team

> 生成时间: 2026-07-10T01:35:43.497439+08:00
> 测试总数: 16 | 通过: 14 | 失败: 2

| # | 测试名称 | 变异 | 期望非零退出 | 实际退出码 | 被拒绝 | 结果 |
|---|----------|------|-------------|-----------|--------|------|
| 1 | missing_history_file | 删除 history JSON 文件 | 是 | 1 | ✅ | PASS |
| 2 | invalid_history_json | 写入非法 JSON 内容 | 是 | 1 | ✅ | PASS |
| 3 | runs_count_gt_7 | 构造 10 条 run（超过 7 条限制） | 是 | 1 | ✅ | PASS |
| 4 | duplicate_run_id | 构造重复的 run_id | 是 | 1 | ✅ | PASS |
| 5 | invalid_hash_format | 将 gate_json_sha256_12 改为 ZZZinvalidZZZ | 是 | 1 | ✅ | PASS |
| 6 | known_fake_hash | 插入已知假 hash a1c3e5g7i9k2 | 是 | 1 | ✅ | PASS |
| 7 | latest_gate_fail | latest run gate_overall_verdict=FAIL | 是 | 1 | ✅ | PASS |
| 8 | redteam_not_all_rejected | latest run redteam_all_rejected=false | 是 | 1 | ✅ | PASS |
| 9 | feishu_sent_true | latest run feishu_sent=true | 是 | 1 | ✅ | PASS |
| 10 | webhook_called_true | latest run feishu_webhook_called=true | 是 | 1 | ✅ | PASS |
| 11 | trading_called_true | latest run feishu_trading_called=true | 是 | 1 | ✅ | PASS |
| 12 | missing_00700 | 删除 hk_00700_status 字段 | 是 | 1 | ✅ | PASS |
| 13 | missing_mobile_link | mdns_link_present=false | 是 | 1 | ✅ | PASS |
| 14 | missing_snapshot_file | 删除 latest run 对应的 snapshot 文件 | 是 | 1 | ✅ | PASS |
| 15 | dashboard_missing_history_degrade | 检查 dashboard 是否包含'未生成 pipeline 历史快照'降级提示 | 是 | 1 | ❌ | FAIL |
| 16 | dashboard_invalid_history_degrade | 检查 dashboard 是否包含'pipeline 历史 JSON 解析失败'降级提示 | 是 | 1 | ❌ | FAIL |

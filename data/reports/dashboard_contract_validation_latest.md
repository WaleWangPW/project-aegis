# Dashboard Contract Validation

- Contract: `2.0`
- Type: `ceo_daily_brief_v2`
- Verdict: `PASS`

## Warnings

- {'name': 'legacy_feishu_home_module', 'old_requirement': '首页展示飞书日报', 'reason': '仅适用于 legacy v1', 'v2_replacement': '飞书安全仍由证据层检查', 'safety_unchanged': 'dry_run/sent/webhook/trading'}
- {'name': 'legacy_pipeline_dom', 'old_requirement': '首页保留旧 Pipeline 区块与降级文案', 'reason': '仅适用于 legacy v1', 'v2_replacement': '系统与数据详情及 fetch 失败降级', 'safety_unchanged': '数据路径、降级和哈希检查'}

## Failures

- None

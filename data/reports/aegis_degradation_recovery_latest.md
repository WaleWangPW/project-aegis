# Project Aegis — Degradation Recovery Tests

> Started: 2026-07-10T01:27:06.446230+08:00
> Finished: 2026-07-10T01:27:08.580580+08:00
> Total: 5 | Passed: 5 | Failed: 0

## Test Results

| # | Scenario | Result | Exit Before Restore | Final Gate | Duration |
|---|----------|--------|---------------------|------------|----------|
| 1 | missing_feishu_json | PASS | 0 | 0 | 0.47s |
| 2 | invalid_feishu_json | PASS | 0 | 0 | 0.46s |
| 3 | missing_non_core_report | PASS | 0 | 0 | 0.52s |
| 4 | injected_invalid_hash_gate_fail_then_restore | PASS | 1 | 0 | 0.38s |
| 5 | dashboard_degrade_removed_gate_fail_then_restore | PASS | 1 | 0 | 0.3s |

### Test 1: missing_feishu_json

- **Result**: PASS
- **Backup created**: True
- **Mutation**: feishu_daily_digest_dry_run.json removed
- **Expected**: exit_code=0 (pipeline regenerates feishu JSON)
- **Exit code before restore**: 0
- **Rejected/Recovered**: True
- **Restored**: False
- **Final gate exit code**: 0

### Test 2: invalid_feishu_json

- **Result**: PASS
- **Backup created**: True
- **Mutation**: feishu_daily_digest_dry_run.json content replaced with '{ invalid json'
- **Expected**: exit_code=0 (pipeline regenerates valid JSON)
- **Exit code before restore**: 0
- **Rejected/Recovered**: True
- **Restored**: False
- **Final gate exit code**: 0

### Test 3: missing_non_core_report

- **Result**: PASS
- **Backup created**: True
- **Mutation**: crcl_risk_monitor_latest.md removed
- **Expected**: core pipeline PASS (non-core report missing is acceptable)
- **Exit code before restore**: 0
- **Rejected/Recovered**: True
- **Restored**: True
- **Final gate exit code**: 0

### Test 4: injected_invalid_hash_gate_fail_then_restore

- **Result**: PASS
- **Backup created**: True
- **Mutation**: injected invalid sha256_12 value [REDACTED] into aegis_pipeline_redteam_latest.md
- **Expected**: exit_code != 0 (gate rejects invalid hash)
- **Exit code before restore**: 1
- **Rejected/Recovered**: True
- **Restored**: True
- **Final gate exit code**: 0

### Test 5: dashboard_degrade_removed_gate_fail_then_restore

- **Result**: PASS
- **Backup created**: True
- **Mutation**: replaced '未生成飞书' with empty string in dashboard/index.html
- **Expected**: exit_code != 0 (gate detects missing degrade notice)
- **Exit code before restore**: 1
- **Rejected/Recovered**: True
- **Restored**: True
- **Final gate exit code**: 0

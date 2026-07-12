# Project Aegis — Evidence Pack

> Generated: 2026-07-10T01:28:01.737181+08:00
> Finished: 2026-07-10T01:28:08.986217+08:00
> Overall Verdict: **PASS**

## Command Results

| Step | Name | Exit Code | Duration | Result |
|------|------|-----------|----------|--------|
| 1 | refresh_feishu_dry_run | 0 | 0.03s | PASS |
| 2 | refresh_aegis_daily_digest | 0 | 0.07s | PASS |
| 3 | validate_aegis_daily_digest | 0 | 0.04s | PASS |
| 4 | audit_aegis_pipeline_evidence | 0 | 0.1s | PASS |
| 5 | redteam_aegis_pipeline | 0 | 2.51s | PASS |
| 6 | verify_aegis_evidence_gate | 0 | 0.11s | PASS |
| 7 | full_check | 0 | 2.69s | PASS |

## Gate Verdict

- **Overall**: PASS
- **Failures**: []

### Gate Checks

| Check | Passed |
|-------|--------|
| A_file_existence | ✅ |
| B_real_fingerprints | ✅ |
| C_hash_validity | ✅ |
| C2_claimed_vs_actual_hash | ✅ |
| D_self_hash_strategy | ✅ |
| E_feishu_dry_run_safety | ✅ |
| F_dashboard | ✅ |
| G_makefile_targets | ✅ |
| H_secret_scan | ✅ |
| I_real_send_risk_scan | ✅ |
| J_cross_validation | ✅ |
| K_md_hash_format | ✅ |
| L_doc_duplicate_sections | ✅ |
| M_feishu_hk_symbol | ✅ |

## Redteam Verdict

- **Passed**: 20/20
- **All Rejected**: True

### Redteam Tests

| Test | Rejected | Result |
|------|----------|--------|
| invalid_hash_format_json | ✅ | REJECTED |
| invalid_hash_format_md | ✅ | REJECTED |
| known_fake_hash_present | ✅ | REJECTED |
| mismatched_real_hash | ✅ | REJECTED |
| self_hash_claimed_in_pipeline | ✅ | REJECTED |
| missing_evidence_policy | ✅ | REJECTED |
| false_dry_run | ✅ | REJECTED |
| sent_true | ✅ | REJECTED |
| webhook_called_true | ✅ | REJECTED |
| trading_called_true | ✅ | REJECTED |
| missing_00700 | ✅ | REJECTED |
| missing_crcl | ✅ | REJECTED |
| missing_000002 | ✅ | REJECTED |
| missing_mobile_link | ✅ | REJECTED |
| injected_dummy_secret | ✅ | REJECTED |
| injected_network_send_call | ✅ | REJECTED |
| injected_trading_call | ✅ | REJECTED |
| invalid_dashboard_degrade | ✅ | REJECTED |
| duplicate_makefile_target | ✅ | REJECTED |
| duplicate_doc_section | ✅ | REJECTED |

## Seven-Run Stability

| Run | Exit Code | Duration | Gate SHA | Feishu SHA | Pipeline SHA |
|-----|-----------|----------|----------|------------|--------------|
| 1 | 0 | 0.22s | 3e3830df37e5 | 11a75f21c6fa | 12d5b9c474fb |
| 2 | 0 | 0.23s | 3e3830df37e5 | e461917655ce | 639431648a29 |
| 3 | 0 | 0.21s | 3e3830df37e5 | 360fb57b2844 | bef7f929735b |
| 4 | 0 | 0.22s | 3e3830df37e5 | cce18151a9f6 | dc4197e32033 |
| 5 | 0 | 0.22s | 3e3830df37e5 | b61ee417fdd6 | c7ba58d369ba |
| 6 | 0 | 0.27s | 3e3830df37e5 | 87414e547d1c | dcd63f256547 |
| 7 | 0 | 0.22s | 3e3830df37e5 | 2ba9fe8085bb | 234b18048909 |

## Hash Cross-Validation

| File | Python SHA256_12 | shasum SHA256_12 | Match |
|------|-----------------|------------------|-------|
| scripts/verify_aegis_evidence_gate.py | b96b641fab56 | b96b641fab56 | ✅ |
| scripts/redteam_aegis_pipeline_validator.py | 8056c48917bc | 8056c48917bc | ✅ |
| scripts/build_aegis_evidence_pack.py | 63cdfdf06e1d | 63cdfdf06e1d | ✅ |
| scripts/run_aegis_degradation_recovery_tests.py | 6a4db3dbfd38 | 6a4db3dbfd38 | ✅ |
| data/reports/aegis_evidence_gate_latest.json | 3e3830df37e5 | 3e3830df37e5 | ✅ |
| data/reports/aegis_pipeline_redteam_latest.json | 63c8814b7e00 | 63c8814b7e00 | ✅ |
| data/reports/aegis_pipeline_evidence_audit_latest.json | dd1aa4ec243a | dd1aa4ec243a | ✅ |
| data/reports/aegis_daily_digest_pipeline_latest.json | 234b18048909 | 234b18048909 | ✅ |
| data/reports/feishu_daily_digest_dry_run.json | 2ba9fe8085bb | 2ba9fe8085bb | ✅ |
| dashboard/index.html | 529c1596075b | 529c1596075b | ✅ |

## Secret Scan

- **Clean**: ✅
- **Findings**: 0

## Real Send Risk Scan

- **Clean**: ✅
- **Findings**: 0

## Degradation Recovery

- **All Passed**: ✅
- **Passed**: 5/5

## Validation Matrix

| Check | Result |
|-------|--------|
| all_commands_pass | ✅ |
| gate_overall_pass | ✅ |
| gate_all_checks_pass | ✅ |
| gate_no_failures | ✅ |
| redteam_passed_ge_20 | ✅ |
| redteam_total_ge_20 | ✅ |
| redteam_all_rejected | ✅ |
| stability_7_runs_all_pass | ✅ |
| hash_cross_validation_all_match | ✅ |
| secret_scan_clean | ✅ |
| real_send_risk_scan_clean | ✅ |
| degradation_recovery_all_pass | ✅ |

## Overall Verdict: **PASS**

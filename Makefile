# Project Aegis Makefile

refresh-feishu-dry-run:
	.venv/bin/python scripts/refresh_feishu_dry_run.py

refresh-aegis-daily-digest:
	.venv/bin/python scripts/refresh_aegis_daily_digest_pipeline.py

validate-aegis-daily-digest:
	.venv/bin/python scripts/validate_aegis_daily_digest_pipeline.py --strict

audit-aegis-pipeline-evidence:
	.venv/bin/python scripts/audit_aegis_pipeline_evidence.py

redteam-aegis-pipeline-validator:
	.venv/bin/python scripts/redteam_aegis_pipeline_validator.py

verify-aegis-evidence-gate-base:
	.venv/bin/python scripts/verify_aegis_evidence_gate.py --strict --write-report --skip-history

verify-aegis-evidence-gate:
	.venv/bin/python scripts/verify_aegis_evidence_gate.py --strict --write-report

full-aegis-daily-digest-check:
	.venv/bin/python scripts/refresh_feishu_dry_run.py
	.venv/bin/python scripts/refresh_aegis_daily_digest_pipeline.py
	.venv/bin/python scripts/validate_aegis_daily_digest_pipeline.py --strict
	.venv/bin/python scripts/audit_aegis_pipeline_evidence.py
	.venv/bin/python scripts/redteam_aegis_pipeline_validator.py
	.venv/bin/python scripts/verify_aegis_evidence_gate.py --strict --write-report

# Pipeline History Management
update-aegis-pipeline-history:
	.venv/bin/python scripts/update_aegis_pipeline_history.py

validate-aegis-pipeline-history:
	.venv/bin/python scripts/validate_aegis_pipeline_history.py --strict

redteam-aegis-pipeline-history:
	.venv/bin/python scripts/redteam_aegis_pipeline_history.py

full-aegis-history-check:
	.venv/bin/python scripts/refresh_feishu_dry_run.py
	.venv/bin/python scripts/refresh_aegis_daily_digest_pipeline.py
	.venv/bin/python scripts/validate_aegis_daily_digest_pipeline.py --strict
	.venv/bin/python scripts/audit_aegis_pipeline_evidence.py
	.venv/bin/python scripts/redteam_aegis_pipeline_validator.py
	.venv/bin/python scripts/verify_aegis_evidence_gate.py --strict --write-report
	.venv/bin/python scripts/update_aegis_pipeline_history.py
	.venv/bin/python scripts/validate_aegis_pipeline_history.py --strict
	.venv/bin/python scripts/build_aegis_evidence_pack.py

# Health Status Management
build-aegis-health-status:
	.venv/bin/python scripts/build_aegis_health_status.py

validate-aegis-health-status:
	.venv/bin/python scripts/validate_aegis_health_status.py --strict

# Strategy Definition
validate-a-share-strategy-definition:
	.venv/bin/python scripts/validate_a_share_strategy_definition.py
run-a-share-backtest-dry-run:
	.venv/bin/python scripts/run_a_share_backtest_dry_run.py

validate-a-share-backtest-dry-run:
	.venv/bin/python scripts/validate_a_share_backtest_dry_run.py

p22-2-filemode:
	.venv/bin/python scripts/run_p22_2_filemode.py

update-a-share-backtest-history:
	.venv/bin/python scripts/update_a_share_backtest_history.py

validate-a-share-backtest-history:
	.venv/bin/python scripts/validate_a_share_backtest_history.py

p22-4-filemode:
	.venv/bin/python scripts/run_p22_4_filemode.py

p22-5-filemode:
	.venv/bin/python scripts/run_p22_5_filemode.py

serve-dashboard:
	.venv/bin/python -m http.server 8080

daily-real-scene-pilot:
	.venv/bin/python scripts/run_aegis_daily_real_scene_pilot.py

daily-real-scene-pilot-dry-run:
	.venv/bin/python scripts/run_aegis_daily_real_scene_pilot.py --send-dry-run

probe-a-share-tushare-strategy-sources:
	.venv/bin/python scripts/probe_a_share_tushare_strategy_sources.py

collect-a-share-dragon-tiger-research-samples:
	.venv/bin/python scripts/collect_a_share_dragon_tiger_research_samples.py

build-a-share-tushare-source-hypotheses:
	.venv/bin/python scripts/build_a_share_tushare_source_hypothesis_queue.py

evaluate-a-share-tushare-source-hypotheses:
	.venv/bin/python scripts/evaluate_a_share_tushare_source_hypotheses.py

build-a-share-tushare-source-feature-coverage:
	.venv/bin/python scripts/build_a_share_tushare_source_feature_coverage.py

evaluate-a-share-tushare-source-deep-sandbox:
	.venv/bin/python scripts/evaluate_a_share_tushare_source_deep_sandbox.py

evaluate-a-share-tushare-refined-strategy-sandbox:
	.venv/bin/python scripts/evaluate_a_share_tushare_refined_strategy_sandbox.py

review-a-share-refined-strategy-ranking-gate:
	.venv/bin/python scripts/review_a_share_refined_strategy_ranking_gate.py

analyze-a-share-tushare-strategy-diagnostics:
	.venv/bin/python scripts/analyze_a_share_tushare_strategy_diagnostics.py

prepare-stock-agent-strategy-simulation:
	.venv/bin/python scripts/prepare_stock_agent_strategy_simulation_workspace.py

stock-agent-a-share-strategy-cycle-managed:
	.venv/bin/python scripts/run_stock_agent_a_share_strategy_cycle.py --prepare-stock-agent-workspace

build-strategy-specific-historical-cases:
	.venv/bin/python scripts/build_aegis_strategy_specific_historical_cases.py

evaluate-strategy-specific-cases:
	.venv/bin/python scripts/evaluate_aegis_strategy_specific_cases.py

stock-agent-a-share-strategy-cycle:
	.venv/bin/python scripts/probe_a_share_tushare_strategy_sources.py
	.venv/bin/python scripts/build_a_share_tushare_source_hypothesis_queue.py
	.venv/bin/python scripts/collect_a_share_dragon_tiger_research_samples.py
	.venv/bin/python scripts/build_aegis_strategy_specific_historical_cases.py
	.venv/bin/python scripts/evaluate_aegis_strategy_specific_cases.py
	.venv/bin/python scripts/evaluate_a_share_tushare_source_hypotheses.py
	.venv/bin/python scripts/build_a_share_tushare_source_feature_coverage.py
	.venv/bin/python scripts/evaluate_a_share_tushare_source_deep_sandbox.py
	.venv/bin/python scripts/evaluate_a_share_tushare_refined_strategy_sandbox.py
	.venv/bin/python scripts/review_a_share_refined_strategy_ranking_gate.py
	.venv/bin/python scripts/analyze_a_share_tushare_strategy_diagnostics.py
	.venv/bin/python scripts/prepare_stock_agent_strategy_simulation_workspace.py

p22-6-full-pipeline:
	.venv/bin/python scripts/run_p22_6_full_pipeline_terminal.py

validate-p23-1-rolling-backtest-design:
	.venv/bin/python scripts/validate_p23_1_rolling_backtest_design.py

generate-a-share-signal-snapshots:
	.venv/bin/python scripts/generate_a_share_signal_snapshots.py

validate-a-share-signal-snapshots:
	.venv/bin/python scripts/validate_a_share_signal_snapshots.py

p23-2-filemode:
	.venv/bin/python scripts/run_p23_2_filemode.py

run-a-share-point-in-time-rolling-backtest:
	.venv/bin/python scripts/run_a_share_point_in_time_rolling_backtest.py

audit-a-share-rolling-backtest-raw-prices:
	.venv/bin/python scripts/audit_a_share_rolling_backtest_raw_prices.py

validate-a-share-point-in-time-rolling-backtest:
	.venv/bin/python scripts/validate_a_share_point_in_time_rolling_backtest.py

update-a-share-rolling-backtest-history:
	.venv/bin/python scripts/update_a_share_rolling_backtest_history.py

validate-a-share-rolling-backtest-history:
	.venv/bin/python scripts/validate_a_share_rolling_backtest_history.py

p23-6-full-rolling-pipeline:
	.venv/bin/python scripts/run_p23_6_full_rolling_pipeline.py

p24-2-hardened-dry-run:
	.venv/bin/python scripts/run_aegis_daily_dry_run_hardened.py

test-p24-2-dry-run-guards:
	.venv/bin/python scripts/test_aegis_daily_dry_run_guards.py

p24-3-double-hardened-simulation:
	.venv/bin/python scripts/run_p24_3_double_hardened_simulation.py

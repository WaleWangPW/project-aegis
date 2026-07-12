# Project Aegis Roadmap

Project Aegis now uses product versions for direction and `Pxx` stages for engineering acceptance. Versions answer "what product are we building"; `Pxx` answers "what evidence has passed".

## Current Baseline

- Accepted engineering baseline: `P25.6 PASS`
- Dashboard Contract: `2.0`
- Production Dashboard SHA256: `e777047e93fc13705df2e6c0dd58728c12ed97ee3f338b512d26ae84b1897a41`
- Current product version: `V2.12-J H-US Virtual PaperTrade Creation From Validated Evidence PASS`
- Current product evidence: `docs/V2_12_J_ACCEPTANCE_REPORT.md`
- Next product target: `V2.12-K H-US Virtual PaperTrade Review/Memory Bridge`
- Active external data source stage: `V2.13-W Finnhub Quote Multi-Symbol
  Sandbox Result Brief PASS`; `CRCL.US`, `MSFT.US`, and `NVDA.US` were evaluated
  and explained as blocked results, with no passed items and no Suggestion Gate
  readiness in this branch.
- Current scope decision: `docs/V2_0_SCOPE_DECISION.md`

`P25.6` proves the Dashboard productization baseline. `V1.0` is accepted by the single-user decision loop evidence in `docs/V1_0_ACCEPTANCE_REPORT.md`.

## Version 1.0: Personal Decision System

Goal: a single-user stock decision system that helps complete daily investment decisions quickly, with evidence, traceability, and review. It is not automatic trading, price prediction, or a quant platform.

V1.0 must include:

- Data foundation: Tushare data, historical cache, point-in-time snapshots, rolling history, rolling backtest, raw price audit, and evidence chain.
- Analysis foundation: Market Regime, Universe Builder, Signal Engine, Expert Committee, Risk Engine, Decision Engine, and `RecommendationRecord`.
- Dashboard: CEO Daily Brief with current conclusion, risk blockers, holdings, executable candidates, watchlist, market state, and data freshness.
- Safety: Evidence Gate, Dashboard Contract, dry run, no real trade, no webhook, no secrets, and hash audit.
- Paper/Review loop: every accepted recommendation can be traced through Entry, Exit or Holding, Review, and Investment Memory.
- Productization: dashboard is readable long term, mobile readable, and contract stable.

V1.0 completion rule:

- At least one `RecommendationRecord` must be traceable through the single-cycle path: `Recommendation -> Paper/Holding -> Review -> Investment Memory`.
- Evidence must include command, exit code, output artifact paths, hashes where relevant, and no marker-only acceptance.
- Empty recommendation days are valid, but V1.0 cannot be accepted only from empty states.

V1.0 acceptance evidence:

- `data/reports/V1_0_SINGLE_CYCLE_ACCEPTANCE_PASS.marker`
- `data/reports/v1_0_single_cycle_acceptance_latest.json`
- `data/reports/v1_0_single_cycle_acceptance_latest.md`
- `data/processed/v1_0_acceptance/v1_0_20260711_acceptance/`

Do not add new Dashboard features or strategy logic just to create more `Pxx` work.

## Version 1.5: Review System

Goal: turn Aegis from a usable personal decision system into a durable review system.

V1.5 adds:

- Weekly Review: weekly return, risk, error, best case, failed case, and lessons.
- Monthly Review: monthly decision report and risk summary.
- Error attribution: why recommendations failed, which risks were missed, which data gaps mattered.
- Investment Memory reuse: future decisions can reference prior successful and failed recommendations.

V1.5 does not change the V1.0 safety boundary. It still does not trade automatically, connect to a broker, or change strategy from review data without explicit approval.

V1.5 acceptance evidence:

- `data/reports/V1_5_REVIEW_SYSTEM_PASS.marker`
- `data/reports/v1_5_review_system_acceptance_latest.json`
- `data/reports/v1_5_review_system_acceptance_latest.md`
- `data/processed/v1_5_acceptance/v1_5_20260711_final_check/`

## Version 2.0: Personal Investment Operating System

Goal: expand from a decision dashboard into a personal investment workflow.

V2.0 recommended scope starts `Portfolio-first`. See
`docs/V2_0_SCOPE_DECISION.md`.

Planned V2.0 capabilities:

- Portfolio: multiple holdings, position sizing, cash management, and risk budget.
- Research Workspace: per-symbol research, notes, timeline, and evidence.
- Event Timeline: announcements, earnings, news, and industry events.
- Strategy Library: growth, value, trend, defensive, or other explicit strategy modes.
- Scenario Analysis: estimate impact from macro or sector scenarios.
- Explainability: every recommendation explains why, why not, why now, and why not later.

V2.0-A acceptance evidence:

- `docs/V2_0_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_0_A_PORTFOLIO_FOUNDATION_PASS.marker`
- `data/reports/v2_0_a_portfolio_foundation_latest.json`
- `data/reports/v2_0_a_portfolio_foundation_latest.md`
- `data/processed/v2_0_a_acceptance/v2_0_a_20260711_acceptance/`

V2.0-B acceptance evidence:

- `docs/V2_0_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_0_B_PORTFOLIO_AWARE_BRIEF_PASS.marker`
- `data/reports/v2_0_b_portfolio_aware_brief_latest.json`
- `data/reports/v2_0_b_portfolio_aware_brief_latest.md`
- `data/processed/v2_0_b_acceptance/v2_0_b_20260711_acceptance/`

V2.0-C acceptance evidence:

- `docs/V2_0_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_0_C_RESEARCH_WORKSPACE_PASS.marker`
- `data/reports/v2_0_c_research_workspace_latest.json`
- `data/reports/v2_0_c_research_workspace_latest.md`
- `data/processed/v2_0_c_acceptance/v2_0_c_20260711_acceptance/`

V2.0-D acceptance evidence:

- `docs/V2_0_D_ACCEPTANCE_REPORT.md`
- `data/reports/V2_0_D_EVENT_TIMELINE_PASS.marker`
- `data/reports/v2_0_d_event_timeline_latest.json`
- `data/reports/v2_0_d_event_timeline_latest.md`
- `data/processed/v2_0_d_acceptance/v2_0_d_20260711_acceptance/`

External market-intelligence planning:

- `docs/EXTERNAL_MARKET_INTELLIGENCE_PLAN.md`

V2.0-E acceptance evidence:

- `docs/V2_0_E_ACCEPTANCE_REPORT.md`
- `data/reports/V2_0_E_EXTERNAL_SOURCE_POLICY_PASS.marker`
- `data/reports/v2_0_e_external_source_policy_latest.json`
- `data/reports/v2_0_e_external_source_policy_latest.md`
- `data/processed/v2_0_e_acceptance/v2_0_e_20260711_acceptance/`

V2.0-F acceptance evidence:

- `docs/V2_0_F_ACCEPTANCE_REPORT.md`
- `data/reports/V2_0_F_OFFICIAL_SOURCE_FETCHER_PASS.marker`
- `data/reports/v2_0_f_official_source_fetcher_latest.json`
- `data/reports/v2_0_f_official_source_fetcher_latest.md`
- `data/processed/v2_0_f_acceptance/v2_0_f_20260711_acceptance_live_sec/`

V2.1-A acceptance evidence:

- `docs/V2_1_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_1_A_HISTORICAL_STRATEGY_SANDBOX_PASS.marker`
- `data/reports/v2_1_a_historical_strategy_sandbox_latest.json`
- `data/reports/v2_1_a_historical_strategy_sandbox_latest.md`
- `data/processed/v2_1_a_acceptance/v2_1_a_20260711_acceptance/`

V2.1-B acceptance evidence:

- `docs/V2_1_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_1_B_STRATEGY_CANDIDATE_LIBRARY_PASS.marker`
- `data/reports/v2_1_b_strategy_candidate_library_latest.json`
- `data/reports/v2_1_b_strategy_candidate_library_latest.md`
- `data/processed/v2_1_b_acceptance/v2_1_b_20260711_acceptance/`

V2.1-C acceptance evidence:

- `docs/V2_1_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_1_C_SUGGESTION_GATE_PASS.marker`
- `data/reports/v2_1_c_suggestion_gate_latest.json`
- `data/reports/v2_1_c_suggestion_gate_latest.md`
- `data/processed/v2_1_c_acceptance/v2_1_c_20260711_acceptance/`

V2.2-A acceptance evidence:

- `docs/V2_2_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_2_A_EXTERNAL_API_RESEARCH_INGESTION_PASS.marker`
- `data/reports/v2_2_a_external_api_research_ingestion_latest.json`
- `data/reports/v2_2_a_external_api_research_ingestion_latest.md`
- `data/processed/v2_2_a_acceptance/v2_2_a_20260711_acceptance/`

V2.2-B acceptance evidence:

- `docs/V2_2_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_2_B_API_BACKED_RESEARCH_FETCH_PASS.marker`
- `data/reports/v2_2_b_api_backed_research_fetch_latest.json`
- `data/reports/v2_2_b_api_backed_research_fetch_latest.md`
- `data/processed/v2_2_b_acceptance/v2_2_b_20260711_acceptance/`

V2.2-C acceptance evidence:

- `docs/V2_2_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_2_C_API_RESEARCH_BRIDGE_PASS.marker`
- `data/reports/v2_2_c_api_research_bridge_latest.json`
- `data/reports/v2_2_c_api_research_bridge_latest.md`
- `data/processed/v2_2_c_acceptance/v2_2_c_20260711_acceptance_rerun/`

V2.3-A acceptance evidence:

- `docs/V2_3_A_ACCEPTANCE_REPORT.md`
- `docs/API_CONFIGURATION_HANDOFF.md`
- `config/external_api_connectors.example.json`
- `data/reports/V2_3_A_API_CONFIGURATION_HANDOFF_PASS.marker`
- `data/reports/v2_3_a_api_configuration_handoff_latest.json`
- `data/reports/v2_3_a_api_configuration_handoff_latest.md`
- `data/processed/v2_3_a_acceptance/v2_3_a_20260711_acceptance/`

V2.3-B acceptance evidence:

- `docs/V2_3_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_3_B_REAL_USER_API_DRY_RUN_PASS.marker`
- `data/reports/v2_3_b_real_user_api_dry_run_latest.json`
- `data/reports/v2_3_b_real_user_api_dry_run_latest.md`
- `data/processed/v2_3_b_acceptance/v2_3_b_20260711_acceptance_final/`

Current implementation target:

- `V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh`: use the
  verified Tushare A-share core data path to refresh a bounded
  simulation-only historical sandbox input. This must not modify strategy
  logic, write production trading records, or produce real trade instructions.
- `V2.11-B User-Provided API Metadata Activation Packet` is accepted by
  `docs/V2_11_B_ACCEPTANCE_REPORT.md`. Tushare is now verified as
  `a_share_core_ready` for daily bars, index bars, stock basic, and trading
  calendar. Sector classification and fundamentals remain `unknown_empty`.
- `V2.11-A Simulation Suggestion Action Packet` is accepted by
  `docs/V2_11_A_ACCEPTANCE_REPORT.md`. It produces a daily simulation-only
  action packet with 6 focus items, 3 blocked paths, and 1 return-evidence
  request.
- `V2.10-D API-Backed Candidate Usable Brief After Real Metadata` is accepted
  by `docs/V2_10_D_ACCEPTANCE_REPORT.md`. Current status is honestly
  `blocked_missing_real_api_artifacts` because V2.10-C still reports
  `blocked_missing_metadata`; therefore Aegis does not yet claim live
  API-backed candidates.
- `V2.9-L Real User Returned Evidence Apply After Local File` remains pending
  until the user supplies `config/user_returned_evidence.local.json`. V2.9-K
  proved the dry-run entrypoint and currently reports
  `blocked_missing_user_returned_evidence` because the local file is absent.
- `V2.8-K API-Backed Candidate Usable Brief After Real Metadata` remains pending
  until real API metadata/env var are available and the real user dry-run
  completes.
- `V2.7-C Real User API Live Dry Run`: run the bounded live API dry-run against
  the user's real connector after non-secret connector metadata exists and the
  required env var is configured locally. This remains research-only and cannot
  write production recommendations directly.
- `V2.3-C Live API Dry Run After User Provides Metadata` remains pending until
  non-secret connector metadata exists and the required env var is set locally
  outside the repo/Vault. This is still research-only and cannot write
  production recommendations directly.

V2.4-A acceptance evidence:

- `docs/V2_4_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_4_A_STRATEGY_RESEARCH_SOURCE_CATALOG_PASS.marker`
- `data/reports/v2_4_a_strategy_research_source_catalog_latest.json`
- `data/reports/v2_4_a_strategy_research_source_catalog_latest.md`
- `data/processed/v2_4_a_acceptance/v2_4_a_20260711_acceptance_final/`

V2.4-B acceptance evidence:

- `docs/V2_4_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_4_B_STRATEGY_RESEARCH_HYPOTHESIS_QUEUE_PASS.marker`
- `data/reports/v2_4_b_strategy_research_hypothesis_queue_latest.json`
- `data/reports/v2_4_b_strategy_research_hypothesis_queue_latest.md`
- `data/processed/v2_4_b_acceptance/v2_4_b_20260711_acceptance/`

V2.4-C acceptance evidence:

- `docs/V2_4_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_4_C_HISTORICAL_SANDBOX_RESEARCH_HYPOTHESES_PASS.marker`
- `data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.json`
- `data/reports/v2_4_c_historical_sandbox_research_hypotheses_latest.md`
- `data/processed/v2_4_c_acceptance/v2_4_c_20260711_acceptance/`

V2.4-D acceptance evidence:

- `docs/V2_4_D_ACCEPTANCE_REPORT.md`
- `data/reports/V2_4_D_RESEARCH_HYPOTHESES_SUGGESTION_GATE_PASS.marker`
- `data/reports/v2_4_d_research_hypotheses_suggestion_gate_latest.json`
- `data/reports/v2_4_d_research_hypotheses_suggestion_gate_latest.md`
- `data/processed/v2_4_d_acceptance/v2_4_d_20260711_acceptance/`

V2.5-A acceptance evidence:

- `docs/V2_5_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_5_A_APPROVED_CANDIDATE_BINDING_PASS.marker`
- `data/reports/v2_5_a_candidate_binding_latest.json`
- `data/reports/v2_5_a_candidate_binding_latest.md`
- `data/processed/v2_5_a_acceptance/v2_5_a_20260711_acceptance/`

V2.5-B acceptance evidence:

- `docs/V2_5_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_5_B_APPROVED_CANDIDATE_REFRESH_PASS.marker`
- `data/reports/v2_5_b_candidate_refresh_latest.json`
- `data/reports/v2_5_b_candidate_refresh_latest.md`
- `data/processed/v2_5_b_acceptance/v2_5_b_20260711_acceptance/`

V2.5-C acceptance evidence:

- `docs/V2_5_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_5_C_USER_API_CANDIDATE_REFRESH_PASS.marker`
- `data/reports/v2_5_c_user_api_candidate_refresh_latest.json`
- `data/reports/v2_5_c_user_api_candidate_refresh_latest.md`
- `data/processed/v2_5_c_acceptance/v2_5_c_20260711_acceptance_rerun/`

V2.6-A acceptance evidence:

- `docs/V2_6_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_6_A_USABLE_SUGGESTION_BRIEF_PASS.marker`
- `data/reports/v2_6_a_usable_suggestion_brief_latest.json`
- `data/reports/v2_6_a_usable_suggestion_brief_latest.md`
- `data/processed/v2_6_a_acceptance/v2_6_a_20260711_acceptance_cn/`

V2.6-B acceptance evidence:

- `docs/V2_6_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_6_B_MANUAL_FEEDBACK_INTAKE_PASS.marker`
- `data/reports/v2_6_b_manual_feedback_intake_latest.json`
- `data/reports/v2_6_b_manual_feedback_intake_latest.md`
- `data/processed/v2_6_b_acceptance/v2_6_b_20260711_acceptance_rerun/`

V2.6-C acceptance evidence:

- `docs/V2_6_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_6_C_FEEDBACK_REVIEW_MEMORY_BRIDGE_PASS.marker`
- `data/reports/v2_6_c_feedback_review_memory_bridge_latest.json`
- `data/reports/v2_6_c_feedback_review_memory_bridge_latest.md`
- `data/processed/v2_6_c_acceptance/v2_6_c_20260711_acceptance/`

V2.7-A acceptance evidence:

- `docs/V2_7_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_7_A_LIVE_API_METADATA_ACTIVATION_PASS.marker`
- `data/reports/v2_7_a_live_api_metadata_activation_latest.json`
- `data/reports/v2_7_a_live_api_metadata_activation_latest.md`
- `data/processed/v2_7_a_acceptance/v2_7_a_20260711_acceptance/`

V2.7-B acceptance evidence:

- `docs/V2_7_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_7_B_LIVE_API_DRY_RUN_PASS.marker`
- `data/reports/v2_7_b_live_api_dry_run_latest.json`
- `data/reports/v2_7_b_live_api_dry_run_latest.md`
- `data/processed/v2_7_b_acceptance/v2_7_b_20260711_acceptance_rerun/`

V2.8-A acceptance evidence:

- `docs/V2_8_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_A_PUBLIC_STRATEGY_SOURCE_AUDIT_PASS.marker`
- `data/reports/v2_8_a_public_strategy_source_audit_latest.json`
- `data/reports/v2_8_a_public_strategy_source_audit_latest.md`
- `data/processed/v2_8_a_acceptance/v2_8_a_20260711_acceptance/`

V2.8-B acceptance evidence:

- `docs/V2_8_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_B_LIVE_PUBLIC_STRATEGY_SOURCE_AUDIT_PASS.marker`
- `data/reports/v2_8_b_live_public_strategy_source_audit_latest.json`
- `data/reports/v2_8_b_live_public_strategy_source_audit_latest.md`
- `data/processed/v2_8_b_acceptance/v2_8_b_20260711_acceptance/`

V2.8-C acceptance evidence:

- `docs/V2_8_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_C_SOURCE_AUDIT_SANDBOX_REFRESH_QUEUE_PASS.marker`
- `data/reports/v2_8_c_source_audit_sandbox_refresh_queue_latest.json`
- `data/reports/v2_8_c_source_audit_sandbox_refresh_queue_latest.md`
- `data/processed/v2_8_c_acceptance/v2_8_c_20260711_acceptance/`

V2.8-D acceptance evidence:

- `docs/V2_8_D_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_D_REFRESH_QUEUE_HISTORICAL_SANDBOX_PASS.marker`
- `data/reports/v2_8_d_refresh_queue_historical_sandbox_latest.json`
- `data/reports/v2_8_d_refresh_queue_historical_sandbox_latest.md`
- `data/processed/v2_8_d_acceptance/v2_8_d_20260711_acceptance/`

V2.8-E acceptance evidence:

- `docs/V2_8_E_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_E_REFRESH_QUEUE_SUGGESTION_GATE_PASS.marker`
- `data/reports/v2_8_e_refresh_queue_suggestion_gate_latest.json`
- `data/reports/v2_8_e_refresh_queue_suggestion_gate_latest.md`
- `data/processed/v2_8_e_acceptance/v2_8_e_20260711_acceptance/`

V2.8-F acceptance evidence:

- `docs/V2_8_F_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_F_REFRESH_QUEUE_USABLE_BRIEF_PASS.marker`
- `data/reports/v2_8_f_refresh_queue_usable_brief_latest.json`
- `data/reports/v2_8_f_refresh_queue_usable_brief_latest.md`
- `data/processed/v2_8_f_acceptance/v2_8_f_20260711_acceptance/`

V2.8-G acceptance evidence:

- `docs/V2_8_G_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_G_CONCRETE_CANDIDATE_BINDING_REFRESH_PASS.marker`
- `data/reports/v2_8_g_concrete_candidate_binding_refresh_latest.json`
- `data/reports/v2_8_g_concrete_candidate_binding_refresh_latest.md`
- `data/processed/v2_8_g_acceptance/v2_8_g_20260711_acceptance/`

V2.8-H acceptance evidence:

- `docs/V2_8_H_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_H_CONCRETE_CANDIDATE_USABLE_BRIEF_PASS.marker`
- `data/reports/v2_8_h_concrete_candidate_usable_brief_latest.json`
- `data/reports/v2_8_h_concrete_candidate_usable_brief_latest.md`
- `data/processed/v2_8_h_acceptance/v2_8_h_20260711_acceptance/`

V2.8-I acceptance evidence:

- `docs/V2_8_I_ACCEPTANCE_REPORT.md`
- `docs/V2_8_I_REAL_USER_API_HANDOFF_REFRESH.md`
- `config/external_api_connectors.user-template.json`
- `data/reports/V2_8_I_REAL_USER_API_HANDOFF_REFRESH_PASS.marker`
- `data/reports/v2_8_i_real_user_api_handoff_refresh_latest.json`
- `data/reports/v2_8_i_real_user_api_handoff_refresh_latest.md`
- `data/processed/v2_8_i_acceptance/v2_8_i_20260711_acceptance/`

V2.8-J acceptance evidence:

- `docs/V2_8_J_ACCEPTANCE_REPORT.md`
- `data/reports/V2_8_J_REAL_USER_API_CANDIDATE_REFRESH_DRY_RUN_PASS.marker`
- `data/reports/v2_8_j_real_user_api_candidate_refresh_dry_run_latest.json`
- `data/reports/v2_8_j_real_user_api_candidate_refresh_dry_run_latest.md`
- `data/processed/v2_8_j_acceptance/v2_8_j_20260711_acceptance/`

V2.9-A acceptance evidence:

- `docs/V2_9_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_A_CURRENT_USER_DECISION_PACKET_PASS.marker`
- `data/reports/v2_9_a_current_user_decision_packet_latest.json`
- `data/reports/v2_9_a_current_user_decision_packet_latest.md`
- `data/processed/v2_9_a_acceptance/v2_9_a_20260711_acceptance/`

V2.9-B acceptance evidence:

- `docs/V2_9_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_B_USER_FEEDBACK_TO_PAPER_SIMULATION_INTAKE_PASS.marker`
- `data/reports/v2_9_b_user_feedback_to_paper_simulation_intake_latest.json`
- `data/reports/v2_9_b_user_feedback_to_paper_simulation_intake_latest.md`
- `data/processed/v2_9_b_acceptance/v2_9_b_20260711_acceptance/`

V2.9-C acceptance evidence:

- `docs/V2_9_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_C_PAPER_SIMULATION_ENTRY_PREP_PASS.marker`
- `data/reports/v2_9_c_paper_simulation_entry_prep_latest.json`
- `data/reports/v2_9_c_paper_simulation_entry_prep_latest.md`
- `data/processed/v2_9_c_acceptance/v2_9_c_20260711_acceptance/`

V2.9-D acceptance evidence:

- `docs/V2_9_D_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_D_USER_SUPPLIED_PAPER_ENTRY_EVIDENCE_PASS.marker`
- `data/reports/v2_9_d_user_supplied_paper_entry_evidence_latest.json`
- `data/reports/v2_9_d_user_supplied_paper_entry_evidence_latest.md`
- `data/processed/v2_9_d_acceptance/v2_9_d_20260711_acceptance/`

V2.9-E acceptance evidence:

- `docs/V2_9_E_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_E_VIRTUAL_PAPER_TRADE_CREATION_PASS.marker`
- `data/reports/v2_9_e_virtual_paper_trade_creation_latest.json`
- `data/reports/v2_9_e_virtual_paper_trade_creation_latest.md`
- `data/processed/v2_9_e_acceptance/v2_9_e_20260711_acceptance/`

V2.9-F acceptance evidence:

- `docs/V2_9_F_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_F_VIRTUAL_PAPER_TRADE_REVIEW_MEMORY_BRIDGE_PASS.marker`
- `data/reports/v2_9_f_virtual_paper_trade_review_memory_bridge_latest.json`
- `data/reports/v2_9_f_virtual_paper_trade_review_memory_bridge_latest.md`
- `data/processed/v2_9_f_acceptance/v2_9_f_20260711_acceptance/`

V2.9-G acceptance evidence:

- `docs/V2_9_G_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_G_FORMAL_REVIEW_MEMORY_RECORDS_PASS.marker`
- `data/reports/v2_9_g_formal_review_memory_records_latest.json`
- `data/reports/v2_9_g_formal_review_memory_records_latest.md`
- `data/processed/v2_9_g_acceptance/v2_9_g_20260711_acceptance/`

V2.9-H acceptance evidence:

- `docs/V2_9_H_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_H_CURRENT_USABLE_SIMULATION_BRIEF_PASS.marker`
- `data/reports/v2_9_h_current_usable_simulation_brief_latest.json`
- `data/reports/v2_9_h_current_usable_simulation_brief_latest.md`
- `data/processed/v2_9_h_acceptance/v2_9_h_20260711_acceptance/`

V2.9-I acceptance evidence:

- `docs/V2_9_I_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_I_USER_RETURNED_EVIDENCE_REFRESH_PASS.marker`
- `data/reports/v2_9_i_user_returned_evidence_refresh_latest.json`
- `data/reports/v2_9_i_user_returned_evidence_refresh_latest.md`
- `data/processed/v2_9_i_acceptance/v2_9_i_20260711_acceptance/`

V2.9-J acceptance evidence:

- `docs/V2_9_J_ACCEPTANCE_REPORT.md`
- `config/user_returned_evidence.user-template.json`
- `data/reports/V2_9_J_REAL_USER_RETURNED_EVIDENCE_TEMPLATE_PASS.marker`
- `data/reports/v2_9_j_real_user_returned_evidence_template_latest.json`
- `data/reports/v2_9_j_real_user_returned_evidence_template_latest.md`
- `data/processed/v2_9_j_acceptance/v2_9_j_20260711_acceptance/`

V2.9-K acceptance evidence:

- `docs/V2_9_K_ACCEPTANCE_REPORT.md`
- `data/reports/V2_9_K_REAL_USER_RETURNED_EVIDENCE_DRY_RUN_PASS.marker`
- `data/reports/v2_9_k_real_user_returned_evidence_dry_run_latest.json`
- `data/reports/v2_9_k_real_user_returned_evidence_dry_run_latest.md`
- `data/processed/v2_9_k_acceptance/v2_9_k_20260711_acceptance/`

V2.10-A acceptance evidence:

- `docs/V2_10_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_10_A_CURRENT_OBJECTIVE_CAPABILITY_PACK_PASS.marker`
- `data/reports/v2_10_a_current_objective_capability_pack_latest.json`
- `data/reports/v2_10_a_current_objective_capability_pack_latest.md`
- `data/processed/v2_10_a_acceptance/v2_10_a_20260711_acceptance/`

V2.10-B acceptance evidence:

- `docs/V2_10_B_ACCEPTANCE_REPORT.md`
- `data/reports/V2_10_B_REAL_API_METADATA_INTAKE_PASS.marker`
- `data/reports/v2_10_b_real_api_metadata_intake_latest.json`
- `data/reports/v2_10_b_real_api_metadata_intake_latest.md`
- `data/processed/v2_10_b_acceptance/v2_10_b_20260711_acceptance/`

V2.10-C acceptance evidence:

- `docs/V2_10_C_ACCEPTANCE_REPORT.md`
- `data/reports/V2_10_C_REAL_API_CANDIDATE_REFRESH_LIVE_DRY_RUN_PASS.marker`
- `data/reports/v2_10_c_real_api_candidate_refresh_live_dry_run_latest.json`
- `data/reports/v2_10_c_real_api_candidate_refresh_live_dry_run_latest.md`
- `data/processed/v2_10_c_acceptance/v2_10_c_20260711_acceptance/`

V2.0 must not implement broker integration, real trading, account sync, secrets,
auto-rebalance, or automatic strategy mutation.

## Version 3.0: AI Investment Partner

Goal: long-term assistant behavior around the decision system.

Possible V3.0 capabilities:

- AI Analyst: proactively surfaces opportunities, risks, and anomalies.
- Natural Language: answer questions about why there is no Action, why sell, why hold, or why wait.
- Learning: summarize reviews and suggest improvements, while keeping all strategy changes explicit and reviewed.

Automatic real trading remains forbidden.

## Version 4.0: Enterprise

Future-only. Current work must not implement:

- Multi-user operation
- Permission systems
- Collaboration workflows
- Enterprise audit APIs
- SaaS deployment
- Public API productization

## Out of Scope

The following remain forbidden unless a future version explicitly changes the product charter and the user approves it:

- Automatic trading
- Broker API integration
- Real order placement
- Webhook-driven trading
- Secrets stored in the repo or Vault
- AI self-learning that changes strategy automatically
- Multi-user or SaaS behavior
- Reinforcement learning
- Neural-network price prediction
- High-frequency trading
- Derivatives workflow
- LLM agents negotiating strategy changes autonomously

## Pxx Mapping

| Engineering stage | Product version | Meaning |
|---|---|---|
| `P0` to `P1D.4` | `V1.0 foundation` | Core decision, data, provider, read-only bridge, and early recommendation loop foundations. |
| `P22` to `P24` | `V1.0 evidence foundation` | Rolling history, backtest, schedule simulation, and evidence hardening. |
| `P25` to `P25.6` | `V1.0 dashboard baseline` | Dashboard Contract 2.0, production dashboard, mobile/readability, hash/evidence acceptance. |
| `V1.0 acceptance` | `V1.0 PASS` | Single-cycle `Recommendation -> PaperTrade -> Review -> InvestmentMemory` accepted. |
| `V1.5 acceptance` | `V1.5 PASS` | Weekly/monthly review, error attribution, best/failed cases, and memory reuse accepted. |
| Current scope work | `V2.0 scope decision` | Portfolio-first direction proposed in `docs/V2_0_SCOPE_DECISION.md`. |
| `V2.0-A acceptance` | `V2.0-A PASS` | Read-only portfolio model, cash, exposure, risk budget, snapshot evidence. |
| `V2.0-B acceptance` | `V2.0-B PASS` | Recommendations explained against portfolio state; no trading, broker integration, or Dashboard Contract change. |
| `V2.0-C acceptance` | `V2.0-C PASS` | Bounded per-symbol research notes and evidence links; LLM unverified content is not evidence. |
| `V2.0-D acceptance` | `V2.0-D PASS` | Bounded event notes and scenario summaries that cannot bypass Evidence Gate. |
| `V2.0-E acceptance` | `V2.0-E PASS` | Source permissions before Bloomberg/Reddit/X or other live web ingestion. |
| `V2.0-F acceptance` | `V2.0-F PASS` | Policy-gated live fetch from approved official SEC source; no cookies/secrets/raw storage. |
| `V2.1-A acceptance` | `V2.1-A PASS` | Historical simulation verified strategy candidates with PASS/FAIL metrics before user-facing suggestions. |
| `V2.1-B acceptance` | `V2.1-B PASS` | Persisted A/H/US strategy candidates for reusable sandbox work. |
| `V2.1-C acceptance` | `V2.1-C PASS` | Produced simulation-only suggestion drafts while blocking failed strategy and risk-veto examples. |
| `V2.2-A acceptance` | `V2.2-A PASS` | Registered approved API connector metadata and structured A/H/US strategy research corpus without secrets/raw text/trading access. |
| `V2.2-B acceptance` | `V2.2-B PASS` | Ran approved API-backed fetch dry-run while storing only summary/hash/env var names. |
| `V2.2-C acceptance` | `V2.2-C PASS` | Converted approved API research summary into proposal-only sandbox candidate update. |
| `V2.3-A acceptance` | `V2.3-A PASS` | Prepared user-provided API metadata/env-var handoff without collecting secrets. |
| `V2.3-B acceptance` | `V2.3-B PASS` | Built and validated the bounded API dry-run entrypoint in fixture mode; real user config remains blocked until metadata is provided. |
| Pending user-input work | `V2.3-C Live API Dry Run After User Provides Metadata` | Run bounded live dry-run once non-secret metadata and local env var are available. |
| `V2.4-A acceptance` | `V2.4-A PASS` | Created canonical A/H/US strategy research source catalog; summary-only and requires sandbox before suggestions. |
| `V2.4-B acceptance` | `V2.4-B PASS` | Converted research sources into explicit sandbox hypotheses without auto-applying strategies or producing direct suggestions. |
| `V2.4-C acceptance` | `V2.4-C PASS` | Ran historical sandbox evaluation for six research hypotheses; three passed and three failed with explicit metric/risk reasons. |
| `V2.4-D acceptance` | `V2.4-D PASS` | Converted sandboxed research hypotheses into Suggestion Gate drafts; three simulation-only drafts allowed and three failed hypotheses blocked. |
| `V2.5-A acceptance` | `V2.5-A PASS` | Bound allowed drafts to approved concrete A/US candidates; H-share draft is honestly blocked by missing candidate source. |
| `V2.5-B acceptance` | `V2.5-B PASS` | Added approved refreshable candidate sources and refreshed A/H/US bindings; fixture is honest and not live market data. |
| `V2.5-C acceptance` | `V2.5-C PASS` | Added bounded user API candidate-refresh entrypoint; fixture API path passes and real user config remains blocked until metadata/env vars. |
| `V2.6-A acceptance` | `V2.6-A PASS` | Produced a user-readable simulation-only suggestion brief with three A/H/US candidates and three blocked paths. |
| `V2.6-B acceptance` | `V2.6-B PASS` | Captured user-entered external decisions, notes, and screenshot evidence paths/hashes without enabling real trading. |
| `V2.6-C acceptance` | `V2.6-C PASS` | Linked accepted feedback evidence into review evidence links and memory candidates without mutating reviews, memory, trades, or recommendations. |
| `V2.7-A acceptance` | `V2.7-A PASS` | Added live API metadata activation preflight; fixture ready path passes while current real user config remains `blocked_missing_metadata`. |
| `V2.7-B acceptance` | `V2.7-B PASS` | Added bounded live API dry-run entrypoint; fixture ready path completes, current real user config remains `blocked_missing_metadata`. |
| `V2.8-A acceptance` | `V2.8-A PASS` | Added public strategy source audit shape; fixture reachability covers A/H/US strategy sources while storing metadata/hash only. |
| `V2.8-B acceptance` | `V2.8-B PASS` | Ran live public-source reachability audit; 12 attempted, 8 reachable, 4 fetch errors recorded, metadata/hash only. |
| `V2.8-C acceptance` | `V2.8-C PASS` | Converted live source audit results into A/H/US sandbox refresh proposals while keeping failed sources blocked. |
| `V2.8-D acceptance` | `V2.8-D PASS` | Reran historical sandbox from the V2.8-C refresh queue; 6 hypotheses evaluated, 3 pass, 3 fail, blocked source refs excluded. |
| `V2.8-E acceptance` | `V2.8-E PASS` | Routed V2.8-D sandbox results through Suggestion Gate; 3 simulation-only paper drafts allowed and 3 failed hypotheses blocked. |
| `V2.8-F acceptance` | `V2.8-F PASS` | Converted V2.8-E drafts into a user-readable simulation-only strategy-basket brief with blocked paths visible. |
| `V2.8-G acceptance` | `V2.8-G PASS` | Bound V2.8-E allowed strategy baskets to approved concrete A/H/US fixture candidate sources, with failed paths still blocked. |
| `V2.8-H acceptance` | `V2.8-H PASS` | Converted V2.8-G concrete candidate bindings into a user-readable simulation-only concrete candidate brief. |
| `V2.8-I acceptance` | `V2.8-I PASS` | Prepared exact non-secret connector metadata checklist and user template for replacing fixtures with user-provided API-backed refresh. |
| `V2.8-J acceptance` | `V2.8-J PASS` | Added bounded candidate-refresh dry-run scaffold; fixture path binds A/H/US, real user path is blocked until metadata/env var exist. |
| Pending user-input work | `V2.8-K API-Backed Candidate Usable Brief After Real Metadata` | Convert real API-backed candidate refresh evidence into a user-readable simulation-only brief after real metadata/env var are available. |
| `V2.9-A acceptance` | `V2.9-A PASS` | Combined accepted sandbox, concrete candidate, and API-blocker evidence into a current user-facing simulation decision packet. |
| `V2.9-B acceptance` | `V2.9-B PASS` | Let user mark packet items as watch/ignore/manual external action and attach evidence, creating paper simulation intake candidates without writing PaperTrade. |
| `V2.9-C acceptance` | `V2.9-C PASS` | Prepared pending virtual paper-trade entry requests that require user-supplied entry price/date before PaperTrade creation; no PaperTrade or Recommendation records were written. |
| `V2.9-D acceptance` | `V2.9-D PASS` | Validated user-provided entry price/date/evidence and produced virtual PaperTrade creation candidates without writing PaperTrade or Recommendation records. |
| `V2.9-E acceptance` | `V2.9-E PASS` | Created a run-specific simulation-only virtual PaperTrade ledger from validated evidence without writing production paper_trades.jsonl. |
| `V2.9-F acceptance` | `V2.9-F PASS` | Connected the virtual ledger to review evidence links and investment-memory candidates without writing production review/memory records. |
| `V2.9-G acceptance` | `V2.9-G PASS` | Produced formal simulation ReviewRecord and InvestmentMemory artifacts from virtual-trade candidates without writing production JSONL files. |
| `V2.9-H acceptance` | `V2.9-H PASS` | Refreshed the current user-readable simulation brief from V2.9-A decision packet and V2.9-G review/memory evidence; still no real trading or strategy mutation. |
| `V2.9-I acceptance` | `V2.9-I PASS` | Accepted fixture user-returned outcome evidence, refreshed the simulation review/memory queue and current brief, and blocked secret-like input without production record mutation. |
| `V2.9-J acceptance` | `V2.9-J PASS` | Added stable gitignored local template path for actual user-returned screenshots/text/outcome evidence and proved compatibility with the V2.9-I refresh path. |
| `V2.9-K acceptance` | `V2.9-K PASS` | Added the real local returned-evidence dry-run entrypoint; current status is honestly `blocked_missing_user_returned_evidence` because the local file is absent. |
| Pending user-input work | `V2.9-L Real User Returned Evidence Apply After Local File` | Run the validated path after the user supplies `config/user_returned_evidence.local.json`; no broker, no webhook, no real order, and no secret storage. |
| `V2.10-A acceptance` | `V2.10-A PASS` | Consolidated the four active user objectives into a verifiable capability pack: public online reads partial-ready, historical sandbox ready, A/H/US strategy research ready, and simulation-only suggestions ready. |
| `V2.10-B acceptance` | `V2.10-B PASS` | Added real API metadata intake/readiness preflight; current status is honestly `blocked_missing_metadata` because the local gitignored connector metadata file is absent. |
| `V2.10-C acceptance` | `V2.10-C PASS` | Added bounded real API candidate-refresh live dry-run orchestrator; current real path is blocked before fetch because metadata is absent, while ready/mock path proves A/H/US binding. |
| `V2.10-D acceptance` | `V2.10-D PASS` | Added API-backed candidate usable brief gate; current real path is honestly `blocked_missing_real_api_artifacts` because metadata/artifacts are absent, so no API-backed suggestion is claimed. |
| `V2.11-A acceptance` | `V2.11-A PASS` | Produced a daily simulation-only action packet with 6 focus items, 3 blocked paths, and 1 return-evidence request; no live price, position size, broker/webhook/order, or API-backed claim. |
| `V2.11-B acceptance` | `V2.11-B PASS` | Prepared API metadata activation packet and verified Tushare A-share core live data path: token present, network available, 4 pass, 0 fail, 2 unknown; no token value stored. |
| `V2.11-C acceptance` | `V2.11-C PASS` | Generated Tushare-backed A-share historical sandbox evidence from verified probe + historical cache: 8 A-share cases, 2 strategy candidates, 0 pass / 2 fail; failures are risk evidence, not trade advice. |
| `V2.11-D acceptance` | `V2.11-D PASS` | Consumed V2.11-C Tushare-backed A-share sandbox evidence in Suggestion Gate; 0 allowed suggestions and 2 blocked suggestions, both blocked by `strategy_sandbox_not_passed`. |
| `V2.11-E acceptance` | `V2.11-E PASS` | Refreshed the current action packet after Tushare Gate: removed A-share focus items `600519.SH` and `600036.SH`, kept H/US simulation focus, and surfaced 5 do-not-use paths. |
| `V2.11-F acceptance` | `V2.11-F PASS` | Converted 2 failed Tushare-backed A-share strategies into research-only rebuild proposals; 0 user-facing A-share suggestions, 0 auto-applied strategy changes, and both proposals remain blocked until sandbox + Suggestion Gate pass. |
| `V2.11-G acceptance` | `V2.11-G PASS` | Ran the rebuilt A-share proposals through 48 expanded Tushare-cache historical cases; 0 pass / 2 fail, so A-share reentry remains blocked. |
| `V2.12-A acceptance` | `V2.12-A PASS` | Verified user-provided EODHD and Twelve Data env vars through secret-safe live probes: EODHD H/US passed, Twelve Data US passed, Twelve Data H recorded fetch failure for later routing/plan review. |
| `V2.12-B acceptance` | `V2.12-B PASS` | Converted V2.12-A capabilities into non-secret H/US provider route proposals: EODHD primary for H daily bars, EODHD primary plus Twelve Data fallback for US daily bars, and Twelve Data H blocked pending plan/symbol proof. No production provider config or suggestion path was enabled. |
| `V2.12-C acceptance` | `V2.12-C PASS` | Used V2.12-B metadata to run a bounded live H/US historical-cache readiness dry run. Wrote run-specific normalized CSV samples for EODHD H, EODHD US, and Twelve Data US with hashes; production cache/config and suggestion paths were not touched. |
| `V2.12-D acceptance` | `V2.12-D PASS` | Converted V2.12-C normalized cache samples into preliminary H/US historical sandbox candidates and cases. Sandbox wiring passed with 2 preliminary strategy passes from 3 cases, while user-facing suggestions remained explicitly disabled. |
| `V2.12-E acceptance` | `V2.12-E PASS` | Routed V2.12-D preliminary H/US sandbox evidence through Suggestion Gate and produced 2 simulation-only paper candidate drafts with evidence refs, sample-size warnings, and manual external execution boundaries. |
| `V2.12-F acceptance` | `V2.12-F PASS` | Turned the gated H/US simulation-only drafts into a concise user-readable brief with 2 H/US simulation candidates, visible sandbox metrics, evidence refs, and no real-trade semantics. |
| `V2.12-G acceptance` | `V2.12-G PASS` | Added evidence-only feedback intake for the H/US simulation brief: accepted watch/ignore/manual external notes, blocked unknown/secret-like inputs, and produced 2 simulation follow-up candidates without mutating production records. |
| `V2.12-H acceptance` | `V2.12-H PASS` | Converted the 2 accepted H/US simulation follow-up candidates into pending review queue items. Each item still requires user-supplied entry price, entry date, evidence reference or screenshot, and explicit simulation confirmation before any virtual PaperTrade validation. |
| `V2.12-I acceptance` | `V2.12-I PASS` | Validated H/US user-supplied paper evidence from the V2.12-H queue: 1 valid item became a virtual PaperTrade creation candidate and 1 incomplete item was blocked. No production records, live prices, broker APIs, webhooks, or orders were used. |
| `V2.12-J acceptance` | `V2.12-J PASS` | Consumed the validated H/US creation candidate and created 1 run-specific simulation-only virtual PaperTrade ledger record while preserving queue/follow-up/feedback/evidence links and leaving production records unchanged. |
| Current implementation target | `V2.12-K H-US Virtual PaperTrade Review/Memory Bridge` | Convert the run-specific H/US virtual ledger into review evidence links and investment-memory candidates without writing production Review or Memory records. |
| External data probe | `V2.13-A PASS` | Finnhub free probe passed after Codex restart: `quote` is reachable, `social_sentiment` is explicitly `blocked_plan_or_rate_limit`, and no token, request URL, or raw payload was stored. Evidence: `docs/V2_13_A_PROBE_REPORT.md`, `data/reports/V2_13_A_FINNHUB_FREE_PROBE_PASS.marker`. |
| External data metadata | `V2.13-B PASS` | Converted Finnhub probe evidence into metadata-only route proposals: quote is ready for metadata routing, social sentiment remains plan/rate-limit blocked, production provider config was not mutated, and suggestion path was not enabled. Evidence: `docs/V2_13_B_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_B_FINNHUB_METADATA_ACTIVATION_PASS.marker`. |
| External data cache readiness | `V2.13-C PASS` | Used Finnhub quote metadata to fetch and write a run-specific normalized quote sample for `AAPL.US`; production cache/provider config were not mutated, social sentiment remains blocked, and suggestion path was not enabled. Evidence: `docs/V2_13_C_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_C_FINNHUB_QUOTE_CACHE_READINESS_PASS.marker`. |
| External quote research context | `V2.13-D PASS` | Converted the verified V2.13-C Finnhub quote artifact into research-context evidence for `AAPL.US`; no network was used in this bridge, social sentiment stayed blocked, and no suggestion, production cache, provider config, broker, webhook, order, or position-size path was enabled. Evidence: `docs/V2_13_D_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_D_FINNHUB_QUOTE_RESEARCH_CONTEXT_PASS.marker`. |
| External quote sandbox binding | `V2.13-E PASS` | Bound the V2.13-D `AAPL.US` quote context to a sandbox candidate packet with status `bound_pending_historical_cases`; no historical sandbox result or user-facing suggestion was claimed, and broker/webhook/order/position-size paths stayed disabled. Evidence: `docs/V2_13_E_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_E_FINNHUB_QUOTE_SANDBOX_BINDING_PASS.marker`. |
| External quote historical cases | `V2.13-F PASS` | Assembled 8 rolling historical cases for the V2.13-E `AAPL.US` sandbox candidate from existing V2.12-C normalized daily bars; sandbox evaluation was not run yet, and no user-facing suggestion or trading path was enabled. Evidence: `docs/V2_13_F_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_F_FINNHUB_QUOTE_HISTORICAL_CASE_ASSEMBLY_PASS.marker`. |
| External quote sandbox evaluation | `V2.13-G PASS` | Evaluated the V2.13-F `AAPL.US` historical cases in the existing sandbox; 1 strategy passed, 0 failed, and Suggestion Gate remains required before any user-facing simulation suggestion. Evidence: `docs/V2_13_G_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_G_FINNHUB_QUOTE_SANDBOX_EVALUATION_PASS.marker`. |
| External quote suggestion gate | `V2.13-H PASS` | Routed the V2.13-G `AAPL.US` Finnhub quote-context sandbox PASS evidence through Suggestion Gate and produced 1 simulation-only `paper_entry_candidate` draft. Social sentiment remains blocked and no real trade, broker API, webhook, live price, order, or position size was enabled. Evidence: `docs/V2_13_H_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_H_FINNHUB_QUOTE_SUGGESTION_GATE_PASS.marker`. |
| External quote simulation brief | `V2.13-I PASS` | Converted the V2.13-H gated draft into a user-readable AAPL.US simulation brief with sample count, win rate, average return, max drawdown, evidence refs, and explicit manual-external-execution boundaries. No real trade, broker API, webhook, live price, order, or position size was enabled. Evidence: `docs/V2_13_I_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_I_FINNHUB_QUOTE_SIMULATION_BRIEF_PASS.marker`. |
| External quote feedback intake | `V2.13-J PASS` | Added evidence-only feedback intake for the V2.13-I AAPL.US simulation brief: accepted watch/ignore/external manual feedback, blocked unknown and secret-like feedback, and produced 2 simulation follow-up candidates without writing PaperTrade, Recommendation, Review, or Memory records. Evidence: `docs/V2_13_J_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_J_FINNHUB_QUOTE_FEEDBACK_INTAKE_PASS.marker`. |
| External quote feedback review queue | `V2.13-K PASS` | Converted the 2 V2.13-J simulation follow-up candidates into pending review queue items requiring user-supplied entry price, entry date, evidence reference or screenshot, explicit simulation confirmation, and explicit review confirmation. No production PaperTrade, Recommendation, Review, Memory, broker API, webhook, live price, order, or position-size path was enabled. Evidence: `docs/V2_13_K_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_K_FINNHUB_QUOTE_FEEDBACK_REVIEW_QUEUE_PASS.marker`. |
| External quote user evidence validation | `V2.13-L PASS` | Validated user-supplied evidence from the V2.13-K Finnhub quote review queue: 1 AAPL.US item became a virtual PaperTrade creation candidate and 1 incomplete item was blocked. No production PaperTrade, Recommendation, Review, Memory, broker API, webhook, live price, order, or position-size path was enabled. Evidence: `docs/V2_13_L_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_L_FINNHUB_QUOTE_USER_SUPPLIED_PAPER_EVIDENCE_PASS.marker`. |
| External quote virtual paper trade | `V2.13-M PASS` | Consumed the V2.13-L validated AAPL.US evidence candidate and created 1 run-specific simulation-only virtual PaperTrade ledger while leaving production `paper_trades.jsonl` unchanged. No Recommendation, Review, Memory, broker API, webhook, live price, order, or position-size path was enabled. Evidence: `docs/V2_13_M_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_M_FINNHUB_QUOTE_VIRTUAL_PAPER_TRADE_CREATION_PASS.marker`. |
| External quote review/memory bridge | `V2.13-N PASS` | Consumed the V2.13-M AAPL.US virtual ledger and produced 1 review evidence link plus 1 investment-memory candidate without writing production Review, Memory, PaperTrade, or Recommendation records. Evidence: `docs/V2_13_N_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_N_FINNHUB_QUOTE_REVIEW_MEMORY_BRIDGE_PASS.marker`. |
| External quote formal review/memory | `V2.13-O PASS` | Consumed the V2.13-N AAPL.US review/memory candidates and produced 1 model-shaped simulation ReviewRecord artifact plus 1 InvestmentMemory artifact without writing production Review, Memory, PaperTrade, or Recommendation records, and without fabricating return, drawdown, exit price, or exit date. Evidence: `docs/V2_13_O_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_O_FINNHUB_QUOTE_FORMAL_REVIEW_MEMORY_PASS.marker`. |
| External quote brief review/memory refresh | `V2.13-P PASS` | Refreshed the current AAPL.US user-readable simulation brief with V2.13-O formal Review/Memory context, showing `formal_pending` status and requiring user-returned outcome evidence before any return, drawdown, exit price, or exit date can be claimed. Evidence: `docs/V2_13_P_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_P_FINNHUB_QUOTE_BRIEF_REVIEW_MEMORY_REFRESH_PASS.marker`. |
| External quote multi-symbol expansion | `V2.13-Q PASS` | Converted the accepted AAPL.US Finnhub context and V2.9-A decision packet into a provider-routed expansion plan: `CRCL.US`, `MSFT.US`, and `NVDA.US` are queued for the next Finnhub quote dry run; A-share candidates route to Tushare, H-share candidates route to the H/US provider branch. No live quote fetch, production record write, strategy mutation, broker API, webhook, order, live price, or position size was enabled. Evidence: `docs/V2_13_Q_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_Q_FINNHUB_QUOTE_MULTI_SYMBOL_EXPANSION_PLAN_PASS.marker`. |
| External quote multi-symbol live probe | `V2.13-R PASS` | Consumed the V2.13-Q Finnhub quote queue and ran bounded live quote probes for `CRCL.US`, `MSFT.US`, and `NVDA.US`; all 3 passed and wrote run-specific normalized JSON/CSV artifacts with hashes. No raw payload, request URL, token value, production record, production cache/config mutation, strategy mutation, suggestion activation, broker API, webhook, order, live order signal, or position size was enabled. Evidence: `docs/V2_13_R_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_R_FINNHUB_QUOTE_MULTI_SYMBOL_LIVE_PROBE_PASS.marker`. |
| External quote multi-symbol research context | `V2.13-S PASS` | Consumed the V2.13-R normalized quote artifacts for `CRCL.US`, `MSFT.US`, and `NVDA.US`; verified artifact hashes and emitted 3 research-context evidence items. This is not a recommendation: sandbox binding/evaluation and Suggestion Gate remain required before any user-facing suggestion. Evidence: `docs/V2_13_S_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_S_FINNHUB_QUOTE_MULTI_SYMBOL_RESEARCH_CONTEXT_PASS.marker`. |
| External quote multi-symbol sandbox binding | `V2.13-T PASS` | Consumed the V2.13-S research-context evidence for `CRCL.US`, `MSFT.US`, and `NVDA.US`; created 3 sandbox candidate packets with status `bound_pending_historical_cases`. No historical sandbox result or user-facing suggestion was claimed. Evidence: `docs/V2_13_T_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_T_FINNHUB_QUOTE_MULTI_SYMBOL_SANDBOX_BINDING_PASS.marker`. |
| External quote multi-symbol historical cases | `V2.13-U PASS` | Consumed the V2.13-T sandbox candidate packets for `CRCL.US`, `MSFT.US`, and `NVDA.US`; fetched bounded EODHD daily bars into a run-specific cache and assembled 81 rolling historical cases. Sandbox evaluation was not run yet, and no user-facing suggestion or trading path was enabled. Evidence: `docs/V2_13_U_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_U_FINNHUB_QUOTE_MULTI_SYMBOL_HISTORICAL_CASE_ASSEMBLY_PASS.marker`. |
| External quote multi-symbol sandbox evaluation | `V2.13-V PASS` | Evaluated the V2.13-U 81 rolling historical cases for `CRCL.US`, `MSFT.US`, and `NVDA.US`; all 3 strategy candidates failed sandbox criteria, so `suggestion_gate_ready=false` and no user-facing suggestion was enabled. Evidence: `docs/V2_13_V_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_V_FINNHUB_QUOTE_MULTI_SYMBOL_SANDBOX_EVALUATION_PASS.marker`. |
| External quote multi-symbol result brief | `V2.13-W PASS` | Converted the V2.13-V failed sandbox results into a user-readable blocked-result brief for `CRCL.US`, `MSFT.US`, and `NVDA.US`, explaining that the branch has 3 blocked items, 0 passed items, and no Suggestion Gate readiness. Evidence: `docs/V2_13_W_ACCEPTANCE_REPORT.md`, `data/reports/V2_13_W_FINNHUB_QUOTE_MULTI_SYMBOL_RESULT_BRIEF_PASS.marker`. |
| External post-blocked candidate refresh | `V2.14-A PASS` | Consumed the V2.13-W blocked-result brief and V2.9-A decision packet, removed `CRCL`, `MSFT`, and `NVDA` from the next candidate pool, retained 6 A/H candidates, and marked US as requiring replacement candidates before historical sandbox and Suggestion Gate. Evidence: `docs/V2_14_A_ACCEPTANCE_REPORT.md`, `data/reports/V2_14_A_POST_BLOCKED_CANDIDATE_REFRESH_PLAN_PASS.marker`. |
| External candidate pool route refresh | `V2.14-B PASS` | Consumed the V2.14-A refresh plan and produced 6 refreshed A/H candidates for the next historical sandbox stage; US remains replacement-only and `CRCL`, `MSFT`, `NVDA` were not reused. Evidence: `docs/V2_14_B_ACCEPTANCE_REPORT.md`, `data/reports/V2_14_B_CANDIDATE_POOL_LIVE_REFRESH_PASS.marker`. |
| External refreshed candidate sandbox | `V2.14-C PASS` | Evaluated the V2.14-B refreshed A/H candidates against available historical evidence: 3 candidates covered, 3 blocked for missing coverage, 1 strategy passed, and 1 strategy failed. User-facing suggestions remain disabled until Suggestion Gate. Evidence: `docs/V2_14_C_ACCEPTANCE_REPORT.md`, `data/reports/V2_14_C_REFRESHED_CANDIDATE_HISTORICAL_SANDBOX_PASS.marker`. |
| External refreshed candidate suggestion gate | `V2.14-D PASS` | Consumed V2.14-C sandbox evidence through Suggestion Gate: 1 simulation-only draft allowed for `00700.HK`, and 5 symbols remain blocked by missing coverage or failed sandbox evidence. Evidence: `docs/V2_14_D_ACCEPTANCE_REPORT.md`, `data/reports/V2_14_D_REFRESHED_CANDIDATE_SUGGESTION_GATE_PASS.marker`. |
| External refreshed candidate simulation brief | `V2.14-E PASS` | Converted the V2.14-D allowed draft into a user-readable simulation brief: current simulation candidate is `00700.HK`, with 5 blocked symbols still visible. Evidence: `docs/V2_14_E_ACCEPTANCE_REPORT.md`, `data/reports/V2_14_E_REFRESHED_CANDIDATE_SIMULATION_BRIEF_PASS.marker`. |
| Pending user-input work | `V2.7-C Real User API Live Dry Run` | Run bounded live API dry-run after user provides non-secret metadata and local env var. |

Rule: do not create a new `Pxx` stage unless it maps to an explicit version target and has a bounded acceptance gate.

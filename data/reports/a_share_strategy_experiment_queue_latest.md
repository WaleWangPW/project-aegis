# A-share Strategy Experiment Queue

- Status: `PASS`
- Generated At: `2026-07-13T01:47:01+08:00`
- Experiments: `6`
- Ready: `6`
- Blocked: `0`
- Ranking Gate Approved: `0`
- Boundary: experiment planning only; no broker, no order, no trading webhook, no recommendation ranking impact.

## Experiments

| Priority | ID | Status | Target | Success Metric |
| ---: | --- | --- | --- | --- |
| 1 | `exp_a_dragon_tiger_event_signal_split` | `READY_EXISTING_DATA` | 把 24 个样本 / 72 个事件 / 36 个事件对齐 case 拆成正净买入、负净买入、机构席位、拥挤换手等子实验。 | 生成至少 2 个可单独评估的龙虎榜子策略，并继续保持 ranking_gate_approved_count=0 直到单独 gate 通过。 |
| 2 | `exp_a_holder_concentration_coverage_backfill` | `READY_BACKFILL` | 提高 stk_holdernumber 在 A股 historical cases 上的覆盖率，减少 missing/blocked cases。 | stk_holdernumber coverage > 0.70，并能为 refined 组合提供非空 case_features。 |
| 3 | `exp_a_governance_reward_alignment_tighten` | `READY_SIGNAL_REWORK` | 不要继续把宽信号当正向因子；改成更严格的趋势/估值/回撤过滤，或只作为风险否决。 | 重测后 signal_case_count 仍 >= 8，且 win_rate/average_return/drawdown 至少一项明显改善。 |
| 3 | `exp_a_institutional_ownership_stability_tighten` | `READY_SIGNAL_REWORK` | 不要继续把宽信号当正向因子；改成更严格的趋势/估值/回撤过滤，或只作为风险否决。 | 重测后 signal_case_count 仍 >= 8，且 win_rate/average_return/drawdown 至少一项明显改善。 |
| 5 | `exp_a_signal_tuning_result_review` | `READY_TUNING_REVIEW` | 复核主力资金、筹码集中、机构持仓、治理 veto-only 等调优实验是否改善；即便通过也不能直接进推荐。 | 至少 1 个 tuned experiment 指标改善且后续通过 Codex-reviewed refined/ranking gate；在此之前 ranking_impact_allowed=false。 |
| 6 | `exp_a_diagnostics_regression_check` | `READY_REGRESSION_CHECK` | 每次 managed cycle 后比较 priority_action_count、deep fail 和 blocked refined count。 | priority_action_count 下降或阻断原因更具体；不允许仅凭 PASS marker 宣称改善。 |

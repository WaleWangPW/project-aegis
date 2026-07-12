# Stock Agent Strategy Simulation Runbook

Updated At: 2026-07-13

Boundary: Project Aegis is simulation research only. No broker API, no real
order placement, no trading webhook, no secrets, and no automatic strategy
mutation.

## Purpose

OpenClaw `stock-agent` should run the repetitive Aegis strategy maintenance
loop, especially for A-share Tushare strategy modules, so Codex only performs
design review and key acceptance.

## Default A-Share Priority

1. `moneyflow`: 主力资金流向，大单/中单/小单结构。
2. `top_list` / `top_inst`: 龙虎榜和游资/机构席位。
3. `top10_holders` / `top10_floatholders` / `stk_holdernumber`: 机构持仓、
   股东人数和筹码集中。
4. `daily_basic` / `stk_factor`: 估值、换手、流动性、因子基础池。
5. `stk_survey` / governance data: 仅在权限可用时作为线索。

## Stock Agent Daily Loop

Run from the Project Aegis repo:

```bash
make probe-a-share-tushare-strategy-sources
make build-a-share-tushare-source-hypotheses
make collect-a-share-dragon-tiger-research-samples
make build-strategy-specific-historical-cases
make evaluate-strategy-specific-cases
make evaluate-a-share-tushare-source-hypotheses
make build-a-share-tushare-source-feature-coverage
make evaluate-a-share-tushare-source-deep-sandbox
make evaluate-a-share-tushare-refined-strategy-sandbox
make review-a-share-refined-strategy-ranking-gate
make plan-a-share-strategy-sample-expansion
make prepare-stock-agent-strategy-simulation
```

For the current A-share dragon-tiger / hot-money expansion run, use the managed
expanded entry instead of running the collector manually:

```bash
make stock-agent-a-share-strategy-cycle-managed-expanded
```

This passes the approved research-only collection parameters into the managed
cycle:

- `lookback_dates=90`
- `forward_days=20`
- `max_symbols=24`
- `max_events_per_symbol=3`

The managed cycle must record `dynamic_args_source` for the collector command.
Do not treat a one-off expanded collector run as accepted unless the final
`stock_agent_a_share_strategy_cycle_latest.json` still shows the expanded sample
counts after the full cycle completes.

Expected outputs:

- `data/reports/a_share_tushare_strategy_source_probe_latest.json`
- `data/reports/a_share_tushare_source_hypothesis_queue_latest.json`
- `data/reports/a_share_dragon_tiger_research_samples_latest.json`
- `data/reports/a_share_tushare_source_hypothesis_evaluation_latest.json`
- `data/reports/a_share_tushare_source_feature_coverage_latest.json`
- `data/reports/a_share_tushare_source_deep_sandbox_latest.json`
- `data/reports/a_share_tushare_refined_strategy_sandbox_latest.json`
- `data/reports/a_share_refined_strategy_ranking_gate_latest.json`
- `data/reports/a_share_strategy_sample_expansion_plan_latest.json`
- `data/reports/aegis_strategy_specific_historical_cases_latest.json`
- `data/reports/aegis_strategy_specific_case_evaluation_latest.json`
- `~/.openclaw/agents/stock-agent/workspace/project-aegis/AEGIS_STOCK_AGENT_STRATEGY_SIMULATION_TASK.md`

## Dragon-Tiger / Hot-Money Sample Rule

`make collect-a-share-dragon-tiger-research-samples` may use Tushare
`top_list` / `top_inst`, but only to build research samples from dates already
covered by the local historical daily cache and with a 20-trading-day forward
window available. These samples must stay `research_sample_only=true`,
`user_facing_suggestion_allowed=false`, and `real_trade_allowed=false`.

Historical cases created from these samples must use the actual
`event_trade_dates` as entry dates. This prevents using recent hot-money events
as if they were available in older historical windows.

## Escalate To Codex When

- `moneyflow`, `top_list`, or ownership data are blocked by permissions.
- A new strategy module would affect ranking or suggestions.
- Historical cases show materially different results from previous reports.
- Any task touches Dashboard Contract, Evidence Gate, broker, webhook, secrets,
  RecommendationRecord, PaperTrade, ReviewRecord, or InvestmentMemory.

## Output Contract

Stock agent reports must include:

1. Commands and exit codes.
2. PASS / EMPTY / PERMISSION_BLOCKED / ERROR modules.
3. A-share source hypotheses created from PASS modules.
4. Dragon-tiger / hot-money sample count, event count, and event-aligned case count.
5. Per-hypothesis proxy disposition and whether deeper source-specific sandbox is needed.
6. Historical case count and data gaps.
7. Source-specific feature coverage and gaps for moneyflow, dragon-tiger seats,
   holders, holder number, factors, and governance.
8. Deep sandbox disposition: `DEEP_SANDBOX_PASS_CANDIDATE` or `DEEP_SANDBOX_FAIL`.
9. Refined strategy disposition: `REFINED_SANDBOX_PASS_CANDIDATE` or
   `REFINED_SANDBOX_FAIL`. A pass here only means "review by ranking gate",
   not a user-facing recommendation.
10. Ranking gate disposition: approved for simulation sort or blocked by
   sample count, unique-symbol coverage, month coverage, symbol concentration,
   win rate, average return, or drawdown.
11. Sample expansion plan: if ranking gate blocks a candidate, report exact
   next parameters such as lookback dates, max symbols, max events per symbol,
   and the recommended collect command.
12. Which symbols remain simulation candidates, watch-only, or downgraded.
13. Explicit safety statement: no broker, no order, no webhook, no secret output.

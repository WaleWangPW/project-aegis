# Stock Agent Strategy Simulation Runbook

Updated At: 2026-07-12

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
make build-strategy-specific-historical-cases
make evaluate-strategy-specific-cases
make evaluate-a-share-tushare-source-hypotheses
make build-a-share-tushare-source-feature-coverage
make evaluate-a-share-tushare-source-deep-sandbox
make prepare-stock-agent-strategy-simulation
```

Expected outputs:

- `data/reports/a_share_tushare_strategy_source_probe_latest.json`
- `data/reports/a_share_tushare_source_hypothesis_queue_latest.json`
- `data/reports/a_share_tushare_source_hypothesis_evaluation_latest.json`
- `data/reports/a_share_tushare_source_feature_coverage_latest.json`
- `data/reports/a_share_tushare_source_deep_sandbox_latest.json`
- `data/reports/aegis_strategy_specific_historical_cases_latest.json`
- `data/reports/aegis_strategy_specific_case_evaluation_latest.json`
- `~/.openclaw/agents/stock-agent/workspace/project-aegis/AEGIS_STOCK_AGENT_STRATEGY_SIMULATION_TASK.md`

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
4. Per-hypothesis proxy disposition and whether deeper source-specific sandbox is needed.
5. Historical case count and data gaps.
6. Source-specific feature coverage and gaps for moneyflow, dragon-tiger seats,
   holders, holder number, factors, and governance.
7. Deep sandbox disposition: `DEEP_SANDBOX_PASS_CANDIDATE` or `DEEP_SANDBOX_FAIL`.
8. Which symbols remain simulation candidates, watch-only, or downgraded.
9. Explicit safety statement: no broker, no order, no webhook, no secret output.

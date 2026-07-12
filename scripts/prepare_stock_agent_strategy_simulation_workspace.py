#!/usr/bin/env python3
"""Prepare a compact OpenClaw stock-agent task packet for Aegis strategy runs."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STOCK_AGENT_WORKSPACE = Path.home() / ".openclaw" / "agents" / "stock-agent" / "workspace" / "project-aegis"
REPORTS = ROOT / "data" / "reports"

FILES_TO_MIRROR = [
    ROOT / "docs" / "STOCK_AGENT_STRATEGY_SIMULATION_RUNBOOK.md",
    ROOT / "docs" / "STRATEGY_RESEARCH.md",
    REPORTS / "a_share_tushare_strategy_source_probe_latest.json",
    REPORTS / "a_share_tushare_strategy_source_probe_latest.md",
    REPORTS / "a_share_tushare_source_hypothesis_queue_latest.json",
    REPORTS / "a_share_tushare_source_hypothesis_queue_latest.md",
    REPORTS / "a_share_dragon_tiger_research_samples_latest.json",
    REPORTS / "a_share_dragon_tiger_research_samples_latest.md",
    REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.json",
    REPORTS / "a_share_tushare_source_hypothesis_evaluation_latest.md",
    REPORTS / "a_share_tushare_source_feature_coverage_latest.json",
    REPORTS / "a_share_tushare_source_feature_coverage_latest.md",
    REPORTS / "a_share_tushare_source_deep_sandbox_latest.json",
    REPORTS / "a_share_tushare_source_deep_sandbox_latest.md",
    REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.json",
    REPORTS / "a_share_tushare_refined_strategy_sandbox_latest.md",
    REPORTS / "a_share_refined_strategy_ranking_gate_latest.json",
    REPORTS / "a_share_refined_strategy_ranking_gate_latest.md",
    REPORTS / "a_share_tushare_strategy_diagnostics_latest.json",
    REPORTS / "a_share_tushare_strategy_diagnostics_latest.md",
    REPORTS / "aegis_strategy_specific_historical_cases_latest.json",
    REPORTS / "aegis_strategy_specific_case_evaluation_latest.json",
    REPORTS / "stock_selection_workbench_latest.json",
    REPORTS / "stock_agent_a_share_strategy_cycle_latest.json",
    REPORTS / "stock_agent_a_share_strategy_cycle_latest.md",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def copy_if_exists(src: Path, dest_dir: Path) -> dict[str, Any]:
    if not src.exists():
        return {"source": str(src), "copied": False, "reason": "missing"}
    dest = dest_dir / src.name
    shutil.copyfile(src, dest)
    return {"source": str(src), "copied": True, "dest": str(dest)}


def task_text(repo_root: Path) -> str:
    return f"""# OpenClaw Stock Agent Task — Aegis A-share Strategy Simulation

Generated At: {now_iso()}

## Goal

Run Project Aegis A-share strategy simulation maintenance with low token cost.
Prioritize A-share Tushare strategy modules: moneyflow, top_list/top_inst,
top10 holders/floatholders, holder number, daily_basic/stk_factor.

## Scope

- Repo: `{repo_root}`
- Read the compact files in this directory first.
- Allowed commands:
  - `make stock-agent-a-share-strategy-cycle-managed`
  - `make probe-a-share-tushare-strategy-sources`
  - `make build-a-share-tushare-source-hypotheses`
  - `make collect-a-share-dragon-tiger-research-samples`
  - `make build-strategy-specific-historical-cases`
  - `make evaluate-strategy-specific-cases`
  - `make evaluate-a-share-tushare-source-hypotheses`
  - `make build-a-share-tushare-source-feature-coverage`
  - `make evaluate-a-share-tushare-source-deep-sandbox`
  - `make evaluate-a-share-tushare-refined-strategy-sandbox`
  - `make review-a-share-refined-strategy-ranking-gate`
  - `make analyze-a-share-tushare-strategy-diagnostics`
  - `make prepare-stock-agent-strategy-simulation`
- Output must be compact: command, exit code, report path, marker path, blockers.

## Non-goals

- Do not place real trades.
- Do not connect broker API.
- Do not call trading webhook.
- Do not write secrets, API keys, cookies, tokens, or raw Tushare payloads.
- Do not auto-mutate accepted strategies before historical sandbox validation.
- Do not create RecommendationRecord, PaperTrade, ReviewRecord, or InvestmentMemory unless a later Codex-reviewed task explicitly approves it.

## Required Evidence

- `a_share_tushare_strategy_source_probe_latest.json`
- `a_share_tushare_source_hypothesis_queue_latest.json`
- `a_share_dragon_tiger_research_samples_latest.json`
- `a_share_tushare_source_hypothesis_evaluation_latest.json`
- `a_share_tushare_source_feature_coverage_latest.json`
- `a_share_tushare_source_deep_sandbox_latest.json`
- `a_share_tushare_refined_strategy_sandbox_latest.json`
- `a_share_refined_strategy_ranking_gate_latest.json`
- `a_share_tushare_strategy_diagnostics_latest.json`
- `aegis_strategy_specific_historical_cases_latest.json`
- `aegis_strategy_specific_case_evaluation_latest.json`
- `stock_agent_a_share_strategy_cycle_latest.json`
- Any blocking source must be reported as `EMPTY`, `PERMISSION_BLOCKED`, or `ERROR`, not hidden.

## Report Format

Return:

1. Commands run and exit codes.
2. PASS/blocked modules.
3. Candidate symbols affected.
4. Historical case counts and data gaps.
5. Dragon-tiger/hot-money sample counts and event-aligned case counts.
6. Per-hypothesis proxy dispositions: `proxy_pass`, `needs_more_a_share_cases`, or `proxy_fail`.
7. Source-specific feature coverage and gaps for moneyflow/top_list/top_inst/holders/factors.
8. Deep sandbox dispositions: `DEEP_SANDBOX_PASS_CANDIDATE` or `DEEP_SANDBOX_FAIL`.
9. Refined strategy dispositions: `REFINED_SANDBOX_PASS_CANDIDATE` or `REFINED_SANDBOX_FAIL`.
10. Ranking gate disposition: approved for simulation sort or blocked by sample concentration / case coverage.
11. Diagnostics priority actions: feature gap collection, signal tightening, risk veto retest, or hypothesis rework.
12. Whether any strategy can enter simulation research.
13. Confirmation that no broker/order/webhook/secret path was touched.
"""


def prepare(stock_agent_workspace: Path = DEFAULT_STOCK_AGENT_WORKSPACE) -> dict[str, Any]:
    stock_agent_workspace.mkdir(parents=True, exist_ok=True)
    copied = [copy_if_exists(src, stock_agent_workspace) for src in FILES_TO_MIRROR]
    task_path = stock_agent_workspace / "AEGIS_STOCK_AGENT_STRATEGY_SIMULATION_TASK.md"
    task_path.write_text(task_text(ROOT), encoding="utf-8")
    manifest = {
        "generated_at": now_iso(),
        "target_dir": str(stock_agent_workspace),
        "task_path": str(task_path),
        "copied": copied,
        "safety": {
            "simulation_research_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values": True,
        },
    }
    manifest_path = stock_agent_workspace / "aegis_stock_agent_strategy_simulation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare stock-agent strategy simulation task files.")
    parser.add_argument("--stock-agent-workspace", default=str(DEFAULT_STOCK_AGENT_WORKSPACE))
    args = parser.parse_args(argv)
    manifest = prepare(Path(args.stock_agent_workspace))
    print(json.dumps({"status": "PASS", "manifest": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

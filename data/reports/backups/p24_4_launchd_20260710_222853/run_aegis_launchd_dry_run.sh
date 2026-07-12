#!/bin/bash
set -eo pipefail

REPO="/Users/weihongwang/Library/Mobile Documents/iCloud~md~obsidian/Documents/LLM-Wiki-Vault/workstations/stock-trading/projects/project-aegis/repo"
LOG="$REPO/data/logs/aegis_launchd_dry_run.log"

cd "$REPO"

{
  echo "============================================================"
  echo "launchd dry-run started: $(date -Iseconds)"
  echo "pid=$$"

  test -f data/reports/P24_2_HARDENED_DRY_RUN_PASS.marker
  test -f data/reports/P24_3_DOUBLE_HARDENED_SIMULATION_PASS.marker
  test -f data/reports/P23_6_FULL_ROLLING_PIPELINE_PASS.marker

  .venv/bin/python scripts/run_aegis_daily_dry_run_hardened.py

  echo "launchd dry-run finished: $(date -Iseconds)"
} >> "$LOG" 2>&1

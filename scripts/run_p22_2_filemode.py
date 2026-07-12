
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

PASS_MARKER = REPORTS / "P22_2_BACKTEST_DRY_RUN_PASS.marker"
FAIL_MARKER = REPORTS / "P22_2_BACKTEST_DRY_RUN_FAIL.marker"
FAIL_REASON = REPORTS / "P22_2_BACKTEST_DRY_RUN_FAIL_REASON.md"
EVIDENCE_JSON = REPORTS / "p22_2_backtest_dry_run_evidence.json"
EVIDENCE_MD = REPORTS / "p22_2_backtest_dry_run_evidence.md"

for p in [PASS_MARKER, FAIL_MARKER]:
    if p.exists():
        p.unlink()

commands = [
    "make validate-a-share-strategy-definition",
    "make run-a-share-backtest-dry-run",
    "make validate-a-share-backtest-dry-run",
    "make validate-aegis-health-status",
    "make verify-aegis-evidence-gate",
]

results = []
success = True

for cmd in commands:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        shell=True,
        text=True,
        capture_output=True,
        timeout=900,
    )
    result = {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }
    results.append(result)
    if proc.returncode != 0:
        success = False

output_files = {
    "backtest_json": "data/reports/a_share_backtest_dry_run_latest.json",
    "backtest_md": "data/reports/a_share_backtest_dry_run_latest.md",
    "input_json": "data/reports/a_share_backtest_dry_run_input_latest.json",
    "validation_json": "data/reports/p22_2_backtest_dry_run_validation_latest.json",
}

file_status = {
    k: (ROOT / v).exists()
    for k, v in output_files.items()
}

evidence = {
    "project": "Project Aegis",
    "type": "p22_2_backtest_dry_run_filemode",
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "overall_success": success,
    "command_results": results,
    "file_status": file_status,
    "safety": {
        "dry_run": True,
        "sent": False,
        "webhook_called": False,
        "trading_called": False,
        "cron_modified": False,
    },
}

EVIDENCE_JSON.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

md_lines = [
    "# P22.2 Backtest Dry-run Evidence",
    "",
    f"- overall_success: {success}",
    "",
    "## Command Results",
    "",
    "| command | exit_code |",
    "|---|---:|",
]
for r in results:
    md_lines.append(f"| {r['command']} | {r['exit_code']} |")

md_lines += [
    "",
    "## Output Files",
    "",
]
for k, exists in file_status.items():
    md_lines.append(f"- {k}: {'EXISTS' if exists else 'MISSING'}")

md_lines += [
    "",
    "## Safety",
    "",
    "- dry_run: true",
    "- sent: false",
    "- webhook_called: false",
    "- trading_called: false",
    "- cron_modified: false",
]

EVIDENCE_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

if success:
    PASS_MARKER.write_text("PASS\n", encoding="utf-8")
    if FAIL_REASON.exists():
        FAIL_REASON.unlink()
else:
    FAIL_MARKER.write_text("FAIL\n", encoding="utf-8")
    reason_lines = ["# P22.2 Backtest FAIL Reason", "", "Command failures:"]
    for r in results:
        if r["exit_code"] != 0:
            reason_lines.append("")
            reason_lines.append(f"## {r['command']}")
            reason_lines.append(f"- exit_code: {r['exit_code']}")
            reason_lines.append("")
            reason_lines.append("### stderr_tail")
            reason_lines.append("```")
            reason_lines.append(r["stderr_tail"])
            reason_lines.append("```")
            reason_lines.append("")
            reason_lines.append("### stdout_tail")
            reason_lines.append("```")
            reason_lines.append(r["stdout_tail"])
            reason_lines.append("```")
    FAIL_REASON.write_text("\n".join(reason_lines) + "\n", encoding="utf-8")

raise SystemExit(0 if success else 1)

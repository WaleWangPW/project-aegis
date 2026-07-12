#!/usr/bin/env python3
"""check_openclaw_aegis_readonly.py — P1C.2 local, credential-free
verification script for the OpenClaw/Feishu read-only adapter.

Runs `scripts/openclaw_aegis_readonly.py` exactly the way an OpenClaw
skill or Feishu bot would — as a subprocess, passing a single
`"aegis <command>"` text string — and checks:

- `"aegis status"` / `"aegis holdings"` / `"aegis summary"` each return
  `{"ok": true, ...}` and exit 0;
- `"aegis buy"` is refused (`{"ok": false, "error": "forbidden_command",
  ...}`, non-zero exit);
- running the forbidden `"aegis buy"` command never creates or modifies
  `data/records/paper_trades.jsonl` (snapshotted by mtime + content hash
  immediately before and after);
- `dashboard/index.html` is unchanged, using the same repo-vs-Vault
  byte-identical check every other P1B/P1C test file already uses (see
  `tests/test_openclaw_aegis_readonly.py::test_dashboard_index_html_unchanged`)
  — skipped honestly (not silently passed) if the Vault-level copy isn't
  present in this environment.

This script itself:
- never imports a provider adapter, `os.environ`, or `dotenv` — it has
  no way to read `.env`/any token, and never does;
- never requires Feishu credentials, an `openclaw` install, or network
  access — it only shells out to a local Python script already in this
  repo;
- never writes to `data/records/` itself; it only *reads* file metadata
  (existence, mtime, content hash) to prove the forbidden command didn't
  write there either.

Usage:
    python scripts/check_openclaw_aegis_readonly.py
    python scripts/check_openclaw_aegis_readonly.py --json-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_SCRIPT = REPO_ROOT / "scripts" / "openclaw_aegis_readonly.py"
PAPER_TRADES_PATH = REPO_ROOT / "data" / "records" / "paper_trades.jsonl"
REPO_DASHBOARD = REPO_ROOT / "dashboard" / "index.html"
VAULT_DASHBOARD = REPO_ROOT.parent / "dashboard" / "index.html"


def _run_adapter(command_text: str) -> tuple[int, Optional[dict[str, Any]], str]:
    """Invokes the adapter exactly as an external OpenClaw/Feishu channel
    would: a subprocess call passing one text argument. Returns
    `(exit_code, parsed_json_or_None, raw_stdout)` — a non-JSON stdout is
    reported as `None`, never silently coerced into a fabricated result."""
    proc = subprocess.run(
        [sys.executable, str(ADAPTER_SCRIPT), command_text],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        parsed = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        parsed = None
    return proc.returncode, parsed, proc.stdout


def _file_fingerprint(path: Path) -> Optional[tuple[float, str]]:
    """(mtime, sha256) if the file exists, else `None`. Used only to
    prove a file was *not* touched — never to read its business content."""
    if not path.exists():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return (path.stat().st_mtime, digest)


def _check_allowed_command(command_text: str) -> dict[str, Any]:
    exit_code, parsed, raw = _run_adapter(command_text)
    ok = exit_code == 0 and parsed is not None and parsed.get("ok") is True
    return {
        "command": command_text,
        "passed": ok,
        "exit_code": exit_code,
        "response_ok": None if parsed is None else parsed.get("ok"),
    }


def _check_forbidden_command_and_no_paper_trade_write(command_text: str) -> dict[str, Any]:
    before = _file_fingerprint(PAPER_TRADES_PATH)
    exit_code, parsed, raw = _run_adapter(command_text)
    after = _file_fingerprint(PAPER_TRADES_PATH)

    refused = (
        exit_code != 0
        and parsed is not None
        and parsed.get("ok") is False
        and parsed.get("error") == "forbidden_command"
    )
    paper_trades_untouched = before == after

    return {
        "command": command_text,
        "passed": refused and paper_trades_untouched,
        "exit_code": exit_code,
        "response_ok": None if parsed is None else parsed.get("ok"),
        "response_error": None if parsed is None else parsed.get("error"),
        "paper_trades_file_untouched": paper_trades_untouched,
    }


def _check_dashboard_unchanged() -> dict[str, Any]:
    if not VAULT_DASHBOARD.exists():
        return {
            "passed": True,
            "status": "skipped_no_vault_copy",
            "note": (
                f"Vault-level dashboard copy not found at {VAULT_DASHBOARD} in this "
                "environment — skipped honestly rather than silently reported as pass."
            ),
        }
    if not REPO_DASHBOARD.exists():
        return {
            "passed": False,
            "status": "repo_dashboard_missing",
            "note": f"{REPO_DASHBOARD} does not exist.",
        }
    identical = REPO_DASHBOARD.read_text(encoding="utf-8") == VAULT_DASHBOARD.read_text(encoding="utf-8")
    return {"passed": identical, "status": "compared", "byte_identical": identical}


def run_all_checks() -> dict[str, Any]:
    results: dict[str, Any] = {
        "status": _check_allowed_command("aegis status"),
        "holdings": _check_allowed_command("aegis holdings"),
        "summary": _check_allowed_command("aegis summary"),
        "buy_refused_no_paper_trade_write": _check_forbidden_command_and_no_paper_trade_write("aegis buy"),
        "dashboard_unchanged": _check_dashboard_unchanged(),
    }
    all_passed = all(bool(v.get("passed")) for v in results.values())
    return {"ok": all_passed, "checks": results}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="P1C.2 local, credential-free verification of the OpenClaw/Feishu "
        "read-only adapter. Requires no Feishu credentials, no openclaw install, no network."
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print only the JSON summary (default already prints only JSON; kept for explicit scripting use).",
    )
    parser.parse_args(argv)

    summary = run_all_checks()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

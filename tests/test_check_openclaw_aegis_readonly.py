"""P1C.2 tests for scripts/check_openclaw_aegis_readonly.py.

Proves the local, credential-free OpenClaw/Feishu verification script:
- reports success when the allowed commands (status/holdings/summary)
  pass and the forbidden command (buy) is correctly refused;
- confirms the forbidden command never creates/modifies
  data/records/paper_trades.jsonl;
- never touches .env/tokens/broker/PaperTrade/CRCL special-casing itself;
- the new docs (SKILL scaffold + setup runbook) point only at the
  existing read-only adapter and contain no real-looking secrets.
"""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.check_openclaw_aegis_readonly as checker

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_check_script_reports_ok_true_against_the_real_repo():
    """Required test #3: the check script returns success when the
    allowed commands pass and the forbidden command fails as expected —
    run for real against this repo's own real (committed) fixtures, the
    same way a user would run it from the command line."""
    summary = checker.run_all_checks()
    assert summary["ok"] is True
    assert summary["checks"]["status"]["passed"] is True
    assert summary["checks"]["holdings"]["passed"] is True
    assert summary["checks"]["summary"]["passed"] is True
    assert summary["checks"]["buy_refused_no_paper_trade_write"]["passed"] is True
    assert summary["checks"]["buy_refused_no_paper_trade_write"]["response_error"] == "forbidden_command"


def test_check_script_cli_prints_json_and_exits_zero():
    """Same check, invoked as the actual CLI entry point a user or
    OpenClaw troubleshooting step would run."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_openclaw_aegis_readonly.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_allowed_command_check_fails_closed_when_adapter_reports_not_ok(monkeypatch):
    """If the adapter ever returned ok=false for an allowed command, the
    checker must report that check as failed, not silently pass."""

    def _fake_run_adapter(command_text: str):
        return 0, {"ok": False, "command": command_text.split(" ", 1)[-1]}, "{}"

    monkeypatch.setattr(checker, "_run_adapter", _fake_run_adapter)
    result = checker._check_allowed_command("aegis status")
    assert result["passed"] is False


def test_forbidden_command_check_fails_if_paper_trades_file_changes(monkeypatch, tmp_path):
    """Required test #5: if the paper_trades.jsonl fingerprint changes
    across the forbidden-command call, the checker must fail the check
    — even if the adapter itself correctly reported a refusal. This
    proves the check script is actually verifying the file, not just
    trusting the JSON response."""
    fake_paper_trades = tmp_path / "paper_trades.jsonl"
    fake_paper_trades.write_text('{"existing": "row"}\n', encoding="utf-8")
    monkeypatch.setattr(checker, "PAPER_TRADES_PATH", fake_paper_trades)

    def _fake_run_adapter(command_text: str):
        # Simulate the forbidden command's refusal being correctly
        # reported, but the file changing anyway (the scenario this
        # check exists to catch) — the adapter call itself is the one
        # moment `_check_forbidden_command_and_no_paper_trade_write`
        # takes its "after" fingerprint from, so mutate the file here.
        fake_paper_trades.write_text('{"existing": "row"}\n{"fake": "new row"}\n', encoding="utf-8")
        return 1, {"ok": False, "error": "forbidden_command", "command": "buy"}, "{}"

    monkeypatch.setattr(checker, "_run_adapter", _fake_run_adapter)
    result = checker._check_forbidden_command_and_no_paper_trade_write("aegis buy")
    assert result["paper_trades_file_untouched"] is False
    assert result["passed"] is False


def test_forbidden_command_check_passes_when_file_absent_both_times(monkeypatch, tmp_path):
    fake_paper_trades = tmp_path / "does_not_exist.jsonl"
    monkeypatch.setattr(checker, "PAPER_TRADES_PATH", fake_paper_trades)

    def _fake_run_adapter(command_text: str):
        return 1, {"ok": False, "error": "forbidden_command", "command": "buy"}, "{}"

    monkeypatch.setattr(checker, "_run_adapter", _fake_run_adapter)
    result = checker._check_forbidden_command_and_no_paper_trade_write("aegis buy")
    assert result["passed"] is True
    assert result["paper_trades_file_untouched"] is True


def test_dashboard_check_skips_honestly_when_vault_copy_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(checker, "VAULT_DASHBOARD", tmp_path / "no_such_dashboard.html")
    result = checker._check_dashboard_unchanged()
    assert result["passed"] is True
    assert result["status"] == "skipped_no_vault_copy"


def test_dashboard_check_matches_real_repo_dashboard():
    """Required test #9: dashboard/index.html unchanged, using the same
    canonical byte-identical check every other P1B/P1C test file uses."""
    result = checker._check_dashboard_unchanged()
    assert result["passed"] is True
    assert result["status"] == "compared"
    assert result["byte_identical"] is True


def test_check_script_never_touches_dotenv_or_token():
    """Required test #4: the check script itself never reads .env/any
    token — checked for actual usage patterns, not a bare substring,
    since this module's own docstring legitimately explains what it
    deliberately does NOT do (same convention as every prior P1B/P1C
    token-check test in this repo)."""
    source = inspect.getsource(checker)
    assert "import dotenv" not in source
    assert "load_dotenv(" not in source
    assert "os.environ[" not in source
    assert "os.environ.get(" not in source
    assert "os.getenv(" not in source
    assert "TushareAdapter(" not in source
    assert "import yfinance" not in source
    assert "ProviderRouter(" not in source


def test_check_script_never_constructs_a_paper_trade_or_broker_call():
    source = inspect.getsource(checker)
    assert "PaperTrade(" not in source
    for forbidden in ("place_order(", "submit_order(", ".buy(", ".sell(", "broker_api", "import broker"):
        assert forbidden not in source.lower()


def test_check_script_never_uses_composite_scoring():
    source = inspect.getsource(checker)
    assert "composite_score" not in source.lower()


def test_check_script_does_not_special_case_crcl():
    source = inspect.getsource(checker)
    assert '"CRCL"' not in source
    assert "'CRCL'" not in source
    assert "== CRCL" not in source


def test_check_script_only_writes_nothing_to_records_dir():
    # The checker only ever *reads* file metadata/content to fingerprint
    # paper_trades.jsonl — it must never open that path (or any records
    # path) for writing.
    source = inspect.getsource(checker)
    assert "write_text(" not in source
    assert "open(" not in source or "'w'" not in source


# -- Docs / scaffold checks --------------------------------------------------

SKILL_MD = REPO_ROOT / "docs" / "openclaw" / "project-aegis-readonly" / "SKILL.md"
RUNBOOK_MD = REPO_ROOT / "docs" / "P1C2_OPENCLAW_FEISHU_SETUP_RUNBOOK.md"

# Real-looking secret shapes we must never find in any doc this round
# touches. These are structural patterns (long hex/base62 runs after a
# recognizable Feishu/OpenClaw credential key), not a check for the
# literal word "secret" (which the docs legitimately discuss).
_SECRET_LIKE_PATTERNS = [
    r"app_secret['\"]?\s*[:=]\s*['\"][A-Za-z0-9]{20,}['\"]",
    r"App Secret['\"]?\s*[:=]\s*['\"][A-Za-z0-9]{20,}['\"]",
    r"TUSHARE_TOKEN\s*=\s*[A-Za-z0-9]{20,}",
    r"cli_[a-z0-9]{16,}",
]


def test_skill_scaffold_exists_and_points_to_readonly_adapter():
    """Required test #8: OpenClaw skill/runbook commands point to the
    read-only adapter."""
    assert SKILL_MD.exists()
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "scripts/openclaw_aegis_readonly.py" in text
    assert '"aegis status"' in text
    assert "aegis buy" in text  # documented as forbidden, not as an example to run


def test_runbook_exists_and_has_allowlist_pairing_guidance():
    """Required test #6: Feishu setup docs contain allowlist/pairing
    guidance."""
    assert RUNBOOK_MD.exists()
    text = RUNBOOK_MD.read_text(encoding="utf-8")
    assert "allowlist" in text.lower()
    assert "pairing" in text.lower() or "配对" in text
    assert "mention" in text.lower()


@pytest.mark.parametrize("doc_path", [SKILL_MD, RUNBOOK_MD])
def test_docs_contain_no_placeholder_looking_real_secrets(doc_path: Path):
    """Required test #7: Feishu setup docs do not contain placeholder-
    looking real secrets — scan for actual secret-shaped strings, not a
    bare substring match on words like "secret" that the docs
    legitimately use in prose."""
    import re

    text = doc_path.read_text(encoding="utf-8")
    for pattern in _SECRET_LIKE_PATTERNS:
        assert not re.search(pattern, text), f"{doc_path} matched secret-like pattern {pattern!r}"


def test_runbook_never_touches_dotenv_or_token_reading_instructions():
    # The runbook must never instruct the reader to grep/cat/print .env
    # or a token from within this repo.
    text = RUNBOOK_MD.read_text(encoding="utf-8")
    assert "cat .env" not in text
    assert "print(os.environ" not in text


def test_dashboard_index_html_unchanged():
    """Required test #9 (duplicate coverage, same convention as every
    other P1B/P1C test file)."""
    repo_dashboard = REPO_ROOT / "dashboard" / "index.html"
    vault_dashboard = REPO_ROOT.parent / "dashboard" / "index.html"
    assert repo_dashboard.read_text(encoding="utf-8") == vault_dashboard.read_text(encoding="utf-8")


def test_wrapper_script_has_no_secrets_or_write_operations():
    wrapper = REPO_ROOT / "scripts" / "aegis_openclaw_command.sh"
    assert wrapper.exists()
    text = wrapper.read_text(encoding="utf-8")
    assert "openclaw_aegis_readonly.py" in text
    for forbidden in ("TUSHARE_TOKEN", "APP_SECRET", "app_secret", ".env"):
        assert forbidden not in text

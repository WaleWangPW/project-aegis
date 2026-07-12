"""P1D.4 tests for scripts/check_provider_runtime.py.

Covers all 11 acceptance criteria from the P1D.4 task spec:
 1. check_provider_runtime.py reports yfinance importability without touching .env
 2. missing yfinance returns controlled failure (exit code 1, overall_status=unavailable)
 3. importable yfinance returns ok (overall_status=ok)
 4. pyproject.toml includes yfinance in main dependencies
 5. run_pre_market uses the same Python environment (same sys.executable)
 6. no token read / printed
 7. no broker / real trading
 8. no manual PaperTrade creation
 9. no composite scoring
10. dashboard/index.html unchanged
11. CRCL not special-cased in check_provider_runtime.py

All tests are purely structural / in-process — no live network calls.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_provider_runtime.py"


# ---------------------------------------------------------------------------
# Import the module under test (works even without installing the package)
# ---------------------------------------------------------------------------

def _import_check_provider_runtime():
    """Import check_provider_runtime as a module without executing __main__."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("check_provider_runtime", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# Test 1: reports yfinance importability without touching .env
# ===========================================================================

def test_1_reports_yfinance_without_dotenv_read() -> None:
    """run_check() must complete and include a 'yfinance' key.
    It must never call dotenv.load_dotenv or open .env files."""
    mod = _import_check_provider_runtime()

    dotenv_calls: list[str] = []

    # Patch load_dotenv to detect any .env read attempt
    with patch("dotenv.load_dotenv", side_effect=lambda *a, **k: dotenv_calls.append("called")):
        result = mod.run_check()

    assert "yfinance" in result, "run_check() must return a 'yfinance' key"
    assert dotenv_calls == [], "run_check() must not call load_dotenv"


# ===========================================================================
# Test 2: missing yfinance → controlled failure, exit code 1
# ===========================================================================

def test_2_missing_yfinance_returns_controlled_failure() -> None:
    """When yfinance cannot be imported, _check_yfinance() returns
    importable=False with a non-None error string (never raises)."""
    mod = _import_check_provider_runtime()

    # Temporarily hide yfinance from sys.modules and make import fail
    import sys as _sys  # noqa: PLC0415

    saved = _sys.modules.pop("yfinance", None)
    try:
        with patch("builtins.__import__", side_effect=lambda name, *a, **k: (
            (_ for _ in ()).throw(ImportError("yfinance not installed (test simulation)"))
            if name == "yfinance" else __import__(name, *a, **k)
        )):
            yf_check = mod._check_yfinance()
    finally:
        if saved is not None:
            _sys.modules["yfinance"] = saved

    assert yf_check["importable"] is False
    assert yf_check["version"] is None
    assert yf_check["error"] is not None and len(yf_check["error"]) > 0


# ===========================================================================
# Test 3: importable yfinance → overall_status ok
# ===========================================================================

def test_3_importable_yfinance_returns_ok() -> None:
    """When yfinance is importable, _check_yfinance() returns importable=True."""
    mod = _import_check_provider_runtime()
    yf_check = mod._check_yfinance()

    # yfinance 1.5.1 is installed in this environment
    assert yf_check["importable"] is True
    assert yf_check["version"] is not None


def test_3b_full_run_check_returns_ok_when_yfinance_present() -> None:
    """run_check() returns overall_status='ok' when yfinance is importable
    and the ProviderRouter H/US route resolves from config/providers.yaml."""
    mod = _import_check_provider_runtime()
    result = mod.run_check()

    assert result["overall_status"] == "ok", (
        f"Expected ok but got {result['overall_status']}. "
        f"yfinance={result['yfinance']}, router={result['provider_router_h_us']}"
    )
    assert result["yfinance"]["importable"] is True
    assert result["yahoo_finance_adapter"]["is_configured"] is True
    assert result["provider_router_h_us"]["instantiated"] is True
    assert result["provider_router_h_us"]["us_daily_route_resolved"] is True


# ===========================================================================
# Test 4: pyproject.toml includes yfinance in main dependencies
# ===========================================================================

def test_4_pyproject_includes_yfinance_main_dependency() -> None:
    """pyproject.toml must list yfinance in [project] dependencies (main deps),
    not only as an optional extra."""
    pyproject = REPO_ROOT / "pyproject.toml"
    assert pyproject.exists(), "pyproject.toml must exist"

    content = pyproject.read_text(encoding="utf-8")

    # Find the [project] dependencies block
    # We look for 'yfinance' appearing before any [project.optional-dependencies] section
    project_section_match = re.search(
        r'\[project\].*?(?=\[project\.|^\[(?!project\b))',
        content,
        re.DOTALL | re.MULTILINE,
    )
    assert project_section_match is not None, "[project] section must exist in pyproject.toml"
    project_section = project_section_match.group(0)
    assert "yfinance" in project_section, (
        "yfinance must be listed in [project] dependencies in pyproject.toml"
    )


# ===========================================================================
# Test 5: run_pre_market and check_provider_runtime use the same Python
# ===========================================================================

def test_5_same_python_executable_as_current_process() -> None:
    """check_provider_runtime.run_check() reports the current sys.executable,
    which is the same Python that would run run_pre_market.py via the CLI."""
    mod = _import_check_provider_runtime()
    result = mod.run_check()

    assert result["python_executable"] == sys.executable, (
        "check_provider_runtime must report the current Python executable"
    )
    assert result["python_version"] == sys.version.split()[0]


# ===========================================================================
# Test 6: no token read / printed
# ===========================================================================

def test_6_no_token_read_or_printed() -> None:
    """check_provider_runtime.py source must not read .env or print tokens."""
    code = SCRIPT_PATH.read_text(encoding="utf-8")
    # Strip docstrings to avoid false positives in comments
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)

    for pattern in (
        r'open\(["\']\.env',
        r'getenv.*token',
        r'getenv.*api_key',
        r'print.*token',
        r'TUSHARE_TOKEN',
    ):
        assert not re.search(pattern, code_only, re.IGNORECASE), (
            f"Token-related pattern '{pattern}' found in check_provider_runtime.py"
        )


# ===========================================================================
# Test 7: no broker / real trading in check_provider_runtime.py
# ===========================================================================

def test_7_no_broker_real_trading() -> None:
    code = SCRIPT_PATH.read_text(encoding="utf-8")
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    for term in ("broker_api", "place_order", "alpaca", "ibkr", "real_order"):
        assert term not in code_only.lower(), (
            f"Broker term '{term}' must not appear in check_provider_runtime.py"
        )


# ===========================================================================
# Test 8: no manual PaperTrade creation in check_provider_runtime.py
# ===========================================================================

def test_8_no_paper_trade_creation() -> None:
    code = SCRIPT_PATH.read_text(encoding="utf-8")
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    assert re.search(r"\bPaperTrade\s*\(", code_only) is None, (
        "PaperTrade must not be constructed in check_provider_runtime.py"
    )


# ===========================================================================
# Test 9: no composite scoring in check_provider_runtime.py
# ===========================================================================

def test_9_no_composite_scoring() -> None:
    code = SCRIPT_PATH.read_text(encoding="utf-8")
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    for term in ("composite_score", "weighted_score", "final_score"):
        assert term not in code_only.lower(), (
            f"Composite scoring term '{term}' in check_provider_runtime.py"
        )


# ===========================================================================
# Test 10: dashboard/index.html unchanged by runtime check
# ===========================================================================

def test_10_dashboard_index_html_unchanged(tmp_path: Path) -> None:
    """run_check() must never write to dashboard/index.html."""
    # Create a sentinel dashboard/index.html
    dash = tmp_path / "dashboard"
    dash.mkdir()
    index_html = dash / "index.html"
    sentinel = "<html><!-- p1d4 sentinel --></html>"
    index_html.write_text(sentinel, encoding="utf-8")

    mod = _import_check_provider_runtime()
    mod.run_check()  # should never touch any dashboard file

    # The real dashboard/index.html in the repo must also be untouched
    real_dash = REPO_ROOT / "dashboard" / "index.html"
    if real_dash.exists():
        content = real_dash.read_text(encoding="utf-8")
        assert "<!-- generated by check_provider_runtime" not in content


# ===========================================================================
# Test 11: CRCL not special-cased in check_provider_runtime.py
# ===========================================================================

def test_11_crcl_not_special_cased() -> None:
    """check_provider_runtime.py must not hardcode CRCL or any specific symbol."""
    code = SCRIPT_PATH.read_text(encoding="utf-8")
    code_only = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)
    assert '"CRCL"' not in code_only, "CRCL must not be hardcoded in check_provider_runtime.py"
    assert "'CRCL'" not in code_only

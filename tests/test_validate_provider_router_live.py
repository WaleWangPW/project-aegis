"""P1B.2 tests for scripts/validate_provider_router_live.py.

Fake `yahoo_finance`-shaped provider injected only — no real network or
`yfinance` call from pytest. Also asserts the CLI never reads `.env` or
any token, and always writes a report JSON even in degraded states.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_provider_router_live.py"

_spec = importlib.util.spec_from_file_location("validate_provider_router_live", SCRIPT_PATH)
cli = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("validate_provider_router_live", cli)
_spec.loader.exec_module(cli)  # type: ignore[union-attr]

from aegis.data.provider_router import ProviderRouter  # noqa: E402

_ROUTING_CONFIG = {
    "routing": {
        "daily_bars": {"H": "yahoo_finance", "US": "yahoo_finance"},
        "index_bars": {"H": "yahoo_finance", "US": "yahoo_finance"},
        "stock_basic": {"H": "not_configured", "US": "not_configured"},
    },
    "symbol_mapping": {
        "yahoo_finance": {
            "H": {"symbols": {"00700.HK": "0700.HK"}, "indexes": {"HSI.HI": "^HSI"}},
            "US": {"symbols": {"CRCL": "CRCL"}, "indexes": {"SPX": "^GSPC"}},
        }
    },
}


class _FakeYahooAdapter:
    def __init__(self, rows: int = 3):
        self._rows = rows

    def is_configured(self) -> bool:
        return True

    def get_daily_bars(self, symbol, market, start, end):
        return pd.DataFrame({"trade_date": [f"2026060{i}" for i in range(1, self._rows + 1)], "close": [1.0] * self._rows})

    def get_index_bars(self, index_code, market, start, end):
        return pd.DataFrame({"trade_date": [f"2026060{i}" for i in range(1, self._rows + 1)], "close": [1.0] * self._rows})

    def get_stock_basic(self, market):
        raise AssertionError("should never be called for H/US")


def _fake_router(rows: int = 3) -> ProviderRouter:
    return ProviderRouter(providers={"yahoo_finance": _FakeYahooAdapter(rows)}, routing_config=_ROUTING_CONFIG)


# -- 9: CLI writes report JSON -------------------------------------------


def test_cli_writes_report_json(tmp_path: Path):
    output_path = tmp_path / "provider_router_live_report.json"
    report = cli.run_validate_provider_router_live(
        markets=["H", "US"], output_path=output_path, router=_fake_router(),
    )
    assert output_path.exists()
    on_disk = json.loads(output_path.read_text(encoding="utf-8"))
    assert on_disk["run_id"] == report["run_id"]
    assert on_disk["checks"]


def test_cli_main_exits_zero_when_at_least_one_route_passes(tmp_path: Path, monkeypatch):
    output_path = tmp_path / "report.json"
    monkeypatch.setattr(cli, "run_validate_provider_router_live", lambda **kwargs: {
        "run_id": "x", "created_at": "now", "network_attempted": True,
        "checks": [{"check_name": "h_daily_bars", "market": "H", "data_type": "daily_bars",
                    "provider": "yahoo_finance", "sample_symbol": "00700.HK", "mapped_symbol": "0700.HK",
                    "status": "pass", "rows_returned": 5, "warning": None, "error_type": None}],
        "summary": {"pass_count": 1, "fail_count": 0, "unknown_count": 0, "skipped_count": 0,
                    "not_configured_count": 0, "dependency_missing_count": 0,
                    "network_unavailable_count": 0, "unsupported_count": 0},
    })
    exit_code = cli.main(["--output", str(output_path)])
    assert exit_code == 0


def test_cli_main_exits_one_when_all_checks_degraded(tmp_path: Path, monkeypatch):
    output_path = tmp_path / "report.json"
    monkeypatch.setattr(cli, "run_validate_provider_router_live", lambda **kwargs: {
        "run_id": "x", "created_at": "now", "network_attempted": False,
        "checks": [{"check_name": "h_daily_bars", "market": "H", "data_type": "daily_bars",
                    "provider": "yahoo_finance", "sample_symbol": "00700.HK", "mapped_symbol": None,
                    "status": "dependency_missing", "rows_returned": None,
                    "warning": "yfinance not installed", "error_type": None}],
        "summary": {"pass_count": 0, "fail_count": 0, "unknown_count": 0, "skipped_count": 0,
                    "not_configured_count": 0, "dependency_missing_count": 1,
                    "network_unavailable_count": 0, "unsupported_count": 0},
    })
    exit_code = cli.main(["--output", str(output_path)])
    assert exit_code == 1


def test_cli_rejects_unknown_market(tmp_path: Path):
    output_path = tmp_path / "report.json"
    with pytest.raises(cli.ValidateProviderRouterLiveArgumentError):
        cli.run_validate_provider_router_live(markets=["A"], output_path=output_path, router=_fake_router())


def test_cli_main_argument_error_returns_one_not_traceback(tmp_path: Path):
    output_path = tmp_path / "report.json"
    exit_code = cli.main(["--markets", "A", "--output", str(output_path)])
    assert exit_code == 1


# -- 10: CLI does not read .env or token ---------------------------------


def test_cli_module_never_touches_dotenv_or_tushare_token():
    source = inspect.getsource(cli)
    assert "import dotenv" not in source
    assert "load_dotenv(" not in source
    assert "os.environ" not in source.replace("`os.environ`", "")
    assert "os.getenv(" not in source
    assert "TUSHARE_TOKEN" not in source.replace("`TUSHARE_TOKEN`", "")
    assert "TushareAdapter(" not in source
    assert "import TushareAdapter" not in source
    assert "tushare_adapter" not in source


def test_cli_runs_with_injected_router_without_any_env_vars(tmp_path: Path, monkeypatch):
    # Confirms the CLI's core path never needs TUSHARE_TOKEN (or any env
    # var) to be set at all when a router is injected.
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    output_path = tmp_path / "report.json"
    report = cli.run_validate_provider_router_live(markets=["H"], output_path=output_path, router=_fake_router())
    assert report["checks"]

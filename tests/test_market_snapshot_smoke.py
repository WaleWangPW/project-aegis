"""P1B.4 tests — H/US MarketSnapshot smoke run
(`scripts/run_market_snapshot_smoke.py`).

Proves the already-implemented MarketSnapshot layer (`MarketSnapshotService`
+ `MarketRegimeAnalyzer`) actually consumes H/US daily/index bars through
`MarketDataService` + `ProviderRouter`'s `yahoo_finance` route, filters out
any bar dated after the requested `--date`, degrades honestly (never
crashes, never fabricates) on route failure, and never treats CRCL as a
market index. Fake `yahoo_finance` provider only — no real network call.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

import scripts.run_market_snapshot_smoke as smoke_module
from aegis.data.gaps import DataGapRegistry
from aegis.data.provider_router import ProviderRouter
from aegis.data.providers import ProviderError
from aegis.data.yahoo_finance_adapter import YahooFinanceAdapter
from scripts.run_market_snapshot_smoke import run_market_snapshot_smoke

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDERS_CONFIG_PATH = REPO_ROOT / "config" / "providers.yaml"


def _load_real_providers_config() -> dict:
    return yaml.safe_load(PROVIDERS_CONFIG_PATH.read_text(encoding="utf-8"))


def _bars(n: int = 20, start_yyyymmdd: str = "20260601") -> pd.DataFrame:
    """`n` ascending trading-day-like rows, close trending gently upward
    so the analyzer's real rules classify this as a genuine uptrend
    rather than "unknown" (used to prove data actually flowed through)."""
    start = pd.Timestamp(start_yyyymmdd)
    dates = [(start + pd.Timedelta(days=i)).strftime("%Y%m%d") for i in range(n)]
    closes = [100.0 + i for i in range(n)]
    return pd.DataFrame({"trade_date": dates, "close": closes, "vol": [1000 + i for i in range(n)]})


class _RecordingYahoo:
    """Fake `yahoo_finance` adapter — records every call it received so
    tests can confirm the router really sent H/US requests here (with
    the symbol already mapped) rather than guessing/faking coverage."""

    def __init__(self, bars: pd.DataFrame | None = None, raise_error: Exception | None = None):
        self.calls: list[tuple] = []
        self._bars = bars if bars is not None else _bars()
        self._raise_error = raise_error

    def get_daily_bars(self, symbol, market, start, end):
        self.calls.append(("daily_bars", symbol, market, start, end))
        if self._raise_error:
            raise self._raise_error
        return self._bars.copy()

    def get_index_bars(self, index_code, market, start, end):
        self.calls.append(("index_bars", index_code, market, start, end))
        if self._raise_error:
            raise self._raise_error
        return self._bars.copy()


@pytest.fixture
def real_router():
    """A `ProviderRouter` built from the actual `config/providers.yaml`
    routing table (same convention as the P1B.3 integration tests), with
    a fake `yahoo_finance` instance substituted in."""
    config = _load_real_providers_config()
    yahoo = _RecordingYahoo()
    router = ProviderRouter(providers={"yahoo_finance": yahoo}, routing_config=config)
    return router, yahoo


# -- 1/2: H/US smoke uses MarketDataService/ProviderRouter daily/index route --


def test_h_smoke_routes_daily_and_index_through_provider_router_to_yahoo(real_router, tmp_path: Path):
    router, yahoo = real_router
    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["H"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )

    entry = report["results"]["H"]
    assert entry["index_bars_status"] == "pass"
    assert entry["daily_bars_status"] == "pass"
    assert entry["index_bars_provider_route"] == "yahoo_finance"
    assert entry["daily_bars_provider_route"] == "yahoo_finance"
    # Symbol/index already mapped (00700.HK -> 0700.HK, HSI.HI -> ^HSI)
    # before yahoo ever saw the request.
    daily_calls = [c for c in yahoo.calls if c[0] == "daily_bars"]
    index_calls = [c for c in yahoo.calls if c[0] == "index_bars"]
    assert any(c[1] == "0700.HK" and c[2] == "H" for c in daily_calls)
    assert any(c[1] == "^HSI" and c[2] == "H" for c in index_calls)


def test_us_smoke_routes_daily_and_index_through_provider_router_to_yahoo(real_router, tmp_path: Path):
    router, yahoo = real_router
    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["US"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )

    entry = report["results"]["US"]
    assert entry["index_bars_status"] == "pass"
    assert entry["daily_bars_status"] == "pass"
    daily_calls = [c for c in yahoo.calls if c[0] == "daily_bars"]
    index_calls = [c for c in yahoo.calls if c[0] == "index_bars"]
    # CRCL is the US daily sample symbol (identity-mapped); SPX -> ^GSPC
    # for the primary index — CRCL never appears as an index request.
    assert any(c[1] == "CRCL" and c[2] == "US" for c in daily_calls)
    assert any(c[1] == "^GSPC" and c[2] == "US" for c in index_calls)


# -- 3: smoke report schema contains H and US entries --------------------


def test_smoke_report_schema_contains_h_and_us_entries(real_router, tmp_path: Path):
    router, _yahoo = real_router
    output_path = tmp_path / "report.json"
    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["H", "US"],
        router=router,
        output_path=output_path,
        gaps_path=tmp_path / "data_gaps.jsonl",
    )

    assert set(report["results"].keys()) == {"H", "US"}
    for market in ("H", "US"):
        entry = report["results"][market]
        for field in (
            "market", "primary_index_internal_code", "index_bars_status",
            "daily_bars_status", "market_snapshot", "overall_status",
        ):
            assert field in entry
    assert output_path.exists()
    import json
    on_disk = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(on_disk["results"].keys()) == {"H", "US"}


# -- 4: H/US route failure produces a non-crashing, honest report --------


def test_yahoo_route_failure_produces_honest_report_not_crash(real_router, tmp_path: Path):
    router, yahoo = real_router
    yahoo._raise_error = ProviderError("yfinance client/package is not available in this environment")

    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["H", "US"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )

    for market in ("H", "US"):
        entry = report["results"][market]
        assert entry["overall_status"] in ("data_gap", "dependency_missing", "network_unavailable", "unknown")
        assert entry["index_bars_rows_returned"] == 0
        # MarketSnapshot itself must still be produced (never crash), and
        # must not fabricate a trend — it degrades to "unknown".
        assert entry["market_snapshot"]["trend_state"] == "unknown"

    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl").list_gaps()
    assert len(gaps) >= 2
    assert all(g["provider"] == "yahoo_finance" for g in gaps if g["data_type"] in ("daily_bars", "index_bars"))


def test_route_failure_status_classifies_dependency_missing(real_router, tmp_path: Path):
    router, yahoo = real_router
    yahoo._raise_error = ProviderError("yfinance package is not installed")

    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["US"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )

    assert report["results"]["US"]["overall_status"] == "dependency_missing"


# -- 5: no future data — bars after --date are ignored --------------------


def test_no_future_data_bars_after_date_are_filtered_out(real_router, tmp_path: Path):
    router, yahoo = real_router
    # 15 rows within range, plus 5 rows dated after the requested date —
    # the smoke run must exclude the future rows before analysis.
    good = _bars(n=15, start_yyyymmdd="20260601")
    future = pd.DataFrame(
        {
            "trade_date": ["20260716", "20260717", "20260718", "20260719", "20260720"],
            "close": [999.0, 998.0, 997.0, 996.0, 995.0],
            "vol": [1, 1, 1, 1, 1],
        }
    )
    yahoo._bars = pd.concat([good, future], ignore_index=True)

    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["H"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )

    entry = report["results"]["H"]
    # Only the 15 in-range rows should have been counted — the 5 future
    # rows were dropped, not silently included.
    assert entry["index_bars_rows_returned"] == 15
    assert entry["daily_bars_rows_returned"] == 15

    gaps = DataGapRegistry(tmp_path / "data_gaps.jsonl").list_gaps()
    future_data_gaps = [g for g in gaps if g["provider"] == "market_snapshot_smoke"]
    assert len(future_data_gaps) >= 1
    assert "Dropped 5" in future_data_gaps[0]["message"]


# -- 6: CRCL is not special-cased as a market snapshot input --------------


def test_crcl_is_not_treated_as_a_market_index_or_snapshot_input(real_router, tmp_path: Path):
    router, yahoo = real_router
    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["US"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )

    entry = report["results"]["US"]
    # SPX (mapped to ^GSPC) is the primary index — never CRCL.
    assert entry["primary_index_internal_code"] == "SPX"
    assert entry["market_snapshot"]["index_summary"]["primary_index"] == "SPX"
    # CRCL only ever appears as the daily-bars sample symbol, never as
    # part of the produced MarketSnapshot object itself.
    assert entry["daily_bars_sample_symbol"] == "CRCL"
    assert "CRCL" not in str(entry["market_snapshot"])


# -- 7: dashboard/index.html unchanged ------------------------------------


def test_dashboard_index_html_unchanged():
    repo_dashboard = REPO_ROOT / "dashboard" / "index.html"
    vault_dashboard = REPO_ROOT.parent / "dashboard" / "index.html"
    assert repo_dashboard.read_text(encoding="utf-8") == vault_dashboard.read_text(encoding="utf-8")


# -- 8: no OpenClaw/Feishu work --------------------------------------------


def test_smoke_script_has_no_openclaw_or_feishu_references():
    source = inspect.getsource(smoke_module)
    assert "openclaw" not in source.lower()
    assert "feishu" not in source.lower()


# -- 9: no token read/printed ----------------------------------------------


def test_smoke_script_never_touches_dotenv_or_tushare_token():
    # Check actual usage patterns, not a bare substring — the module's own
    # docstrings legitimately *mention* these terms to describe what this
    # script deliberately does NOT do (same convention as the P1B.2/P1B.3
    # token-check tests).
    source = inspect.getsource(smoke_module)
    assert "import dotenv" not in source
    assert "load_dotenv(" not in source
    assert "os.environ[" not in source
    assert "os.environ.get(" not in source
    assert "os.getenv(" not in source
    assert "import TushareAdapter" not in source
    assert "from aegis.data.tushare_adapter" not in source
    assert "TushareAdapter(" not in source


# -- extra: unknown market rejected, no A/Tushare involvement -------------


def test_unknown_market_is_rejected_without_crashing(real_router, tmp_path: Path):
    router, _yahoo = real_router
    with pytest.raises(smoke_module.MarketSnapshotSmokeArgumentError):
        run_market_snapshot_smoke(
            date="2026-06-30",
            markets=["A"],
            router=router,
            output_path=tmp_path / "report.json",
            gaps_path=tmp_path / "data_gaps.jsonl",
        )


def test_snapshot_is_not_purely_unknown_when_bars_actually_flow(real_router, tmp_path: Path):
    """If real bars come back (>=20 ascending closes), MarketRegimeAnalyzer's
    already-accepted rules should classify a genuine trend rather than
    leaving the MarketSnapshot at "unknown" — this is existing Phase 2
    behavior, this test only proves the smoke run doesn't get in its way."""
    router, yahoo = real_router
    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["H"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )
    snapshot = report["results"]["H"]["market_snapshot"]
    assert snapshot["trend_state"] != "unknown"
    assert snapshot["data_quality"]["status"] in ("complete", "partial")


# ===========================================================================
# P1B.4 local smoke failure triage
#
# The user's local Mac run reported H and US both `overall_status=unknown`
# with 0 rows for both index and daily bars, despite `yahoo_finance` being
# named as the route and P1B.2's own live validation already confirming 20
# real rows for the exact same tickers. Root cause: `lookback_range()`
# (used by `MarketSnapshotService`/this smoke script to compute a fetch
# window) produces a compact "YYYYMMDD" string, but the real `yfinance`
# package parses `start`/`end` via a strict `datetime.strptime(dt,
# "%Y-%m-%d")` internally — which raises on a compact string, and
# `yfinance`'s own `_download_one` swallows that exception and substitutes
# an empty DataFrame instead of propagating it. So the caller sees no
# crash, only zero rows. Fixed in `aegis/data/yahoo_finance_adapter.py`
# (`YahooFinanceAdapter._normalize_date_str`), not here — these tests
# prove the fix actually closes the loop through the full real stack: the
# earlier tests in this file used a hand-rolled fake (`_RecordingYahoo`)
# that never cared about date format at all, which is exactly why they
# never caught this bug.
# ===========================================================================


class _StrictDateYfClient:
    """A fake client that mimics the real `yfinance` package's actual
    behavior: only returns real data when `start`/`end` are the dashed
    `"YYYY-MM-DD"` format it truly requires; anything else (e.g. an
    un-normalized compact `"YYYYMMDD"` string) silently comes back empty,
    exactly like the real bug this triage round fixed."""

    _DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def __init__(self, frame_factory):
        self._frame_factory = frame_factory
        self.calls: list[tuple] = []

    def download(self, symbol, start=None, end=None, progress=None):
        self.calls.append((symbol, start, end))
        if not (self._DATE_RE.match(start or "") and self._DATE_RE.match(end or "")):
            return pd.DataFrame()
        return self._frame_factory()


def _real_yfinance_shaped_frame(n: int = 20, start_yyyymmdd: str = "20260601") -> pd.DataFrame:
    """A Date-indexed, Open/High/Low/Close/Volume-columned frame — exactly
    what the real `yfinance.download()` returns, unlike `_bars()`'s
    already-normalized `trade_date`/`close` shape used elsewhere in this
    file for the hand-rolled `_RecordingYahoo` fake."""
    start = pd.Timestamp(start_yyyymmdd)
    idx = pd.date_range(start, periods=n, freq="D")
    closes = [100.0 + i for i in range(n)]
    return pd.DataFrame(
        {
            "Open": closes, "High": [c + 1 for c in closes], "Low": [c - 1 for c in closes],
            "Close": closes, "Volume": [1000 + i for i in range(n)],
        },
        index=idx,
    ).rename_axis("Date")


@pytest.fixture
def real_yahoo_router():
    """A `ProviderRouter` built from the real `config/providers.yaml`,
    wired with a **real** `YahooFinanceAdapter` (not a hand-rolled
    recording fake) whose underlying client is `_StrictDateYfClient` —
    this is the fixture that actually exercises the date-normalization
    fix end to end through the real adapter's `_normalize_date_str`."""
    config = yaml.safe_load(PROVIDERS_CONFIG_PATH.read_text(encoding="utf-8"))
    client = _StrictDateYfClient(lambda: _real_yfinance_shaped_frame())
    yahoo = YahooFinanceAdapter(client=client)
    router = ProviderRouter(providers={"yahoo_finance": yahoo}, routing_config=config)
    return router, client


def test_smoke_returns_real_rows_through_real_yahoo_finance_adapter(real_yahoo_router, tmp_path: Path):
    """The critical regression test for this triage round: runs the full
    smoke path (compact-date `lookback_range` -> `MarketSnapshotService`
    -> `MarketDataService` -> `ProviderRouter` -> the **real**
    `YahooFinanceAdapter`) against a client that only responds to
    correctly-dashed dates — proving the fix actually closes the gap the
    earlier hand-rolled-fake tests could never have caught."""
    router, client = real_yahoo_router
    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["H", "US"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )

    for market in ("H", "US"):
        entry = report["results"][market]
        assert entry["index_bars_rows_returned"] > 0, f"{market} index bars still zero rows"
        assert entry["daily_bars_rows_returned"] > 0, f"{market} daily bars still zero rows"
        assert entry["index_bars_status"] == "pass"
        assert entry["overall_status"] in ("pass", "partial")
        assert entry["market_snapshot"]["trend_state"] != "unknown"

    # Confirm the client actually received dashed dates, not the compact
    # ones `lookback_range` originally produced.
    assert all(
        re.match(r"^\d{4}-\d{2}-\d{2}$", start) and re.match(r"^\d{4}-\d{2}-\d{2}$", end)
        for _symbol, start, end in client.calls
    )


def test_smoke_still_returns_rows_when_date_falls_on_a_weekend(real_yahoo_router, tmp_path: Path):
    """Item 4/7 from the triage task: `--date` itself may be a
    weekend/holiday (2026-07-04 is a Saturday) — the smoke run must still
    return real rows from within its lookback window, not just look at
    the single end date."""
    router, _client = real_yahoo_router
    report = run_market_snapshot_smoke(
        date="2026-07-04",
        markets=["H"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )
    entry = report["results"]["H"]
    assert entry["index_bars_rows_returned"] > 0
    assert entry["overall_status"] in ("pass", "partial")


def test_fetch_window_is_reported_and_lookback_days_is_configurable(real_yahoo_router, tmp_path: Path):
    """Item 1: the smoke report now states the exact fetch window it used
    (transparency requested by the triage task), and `--lookback-days` is
    configurable rather than a hardcoded constant."""
    router, _client = real_yahoo_router
    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["H"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
        lookback_days=45,
    )
    assert report["lookback_days"] == 45
    start = pd.Timestamp(report["fetch_window"]["start"])
    end = pd.Timestamp(report["fetch_window"]["end"])
    assert (end - start).days == 45


def test_no_stale_cache_can_mask_valid_provider_output(real_yahoo_router, tmp_path: Path):
    """Item 8: the smoke run's `MarketDataService` is always constructed
    with `cache=None` — there is no cache layer at all for this smoke
    path, so a stale empty cache entry can never mask real provider
    output. Verified here by running the same smoke command twice after
    the fake client starts returning real data — both runs must see the
    real rows, proving nothing was cached and stale from a hypothetical
    first empty attempt."""
    router, client = real_yahoo_router
    gaps_path = tmp_path / "data_gaps.jsonl"

    first = run_market_snapshot_smoke(
        date="2026-06-30", markets=["H"], router=router,
        output_path=tmp_path / "report1.json", gaps_path=gaps_path,
    )
    second = run_market_snapshot_smoke(
        date="2026-06-30", markets=["H"], router=router,
        output_path=tmp_path / "report2.json", gaps_path=gaps_path,
    )
    assert first["results"]["H"]["index_bars_rows_returned"] > 0
    assert second["results"]["H"]["index_bars_rows_returned"] > 0
    # The fake client was actually called twice (no cache short-circuited
    # the second run) — proving there is no cache to go stale in the first
    # place.
    assert len(client.calls) >= 2


# ===========================================================================
# P1B.4.1 — smoke/snapshot consistency fix
#
# User's newest local report: H/US index+daily routes returned 41 real
# rows via yahoo_finance (status: pass), but the embedded MarketSnapshot
# for both markets still said `DATA_GAP: No index bars available for
# this market/session` with data_quality.status="partial". Root cause:
# this script's own "route pass" status used a naive `len(df) > 0`
# check, while MarketSnapshotService/MarketRegimeAnalyzer correctly
# check `df.empty` (True whenever either axis — including columns — has
# length 0) and `"close" in df.columns`. A real yfinance response can
# have real ROWS but zero usable COLUMNS (e.g. MultiIndex columns the
# adapter's alias-matching didn't recognize before the accompanying
# aegis/data/yahoo_finance_adapter.py fix), so `len(df)` and `df.empty`
# disagreed. Fixed by making this script's own status derive from
# `_bars_are_usable()` — the exact same non-empty + "close"-column +
# minimum-bar-count check the analyzer itself applies — so "route pass"
# and "snapshot has real data" can no longer disagree.
# ===========================================================================


def _real_yfinance_multiindex_shaped_frame(n: int = 41, start_yyyymmdd: str = "20260501") -> pd.DataFrame:
    """Reproduces the exact real-world bug report: a real yfinance
    response with genuine OHLCV data (41 rows) but MultiIndex columns
    (top level = field name, second level = ticker) — a shape some
    installed yfinance versions return by default even for one symbol."""
    start = pd.Timestamp(start_yyyymmdd)
    idx = pd.date_range(start, periods=n, freq="D")
    closes = [100.0 + i for i in range(n)]
    frame = pd.DataFrame(
        {
            "Open": closes, "High": [c + 1 for c in closes], "Low": [c - 1 for c in closes],
            "Close": closes, "Volume": [1000 + i for i in range(n)],
        },
        index=idx,
    ).rename_axis("Date")
    frame.columns = pd.MultiIndex.from_product([frame.columns, ["TICKER"]])
    return frame


class _MultiIndexColumnYfClient:
    """A fake low-level client (mimicking real `yfinance.download`) that
    returns MultiIndex-columned frames — routed through the **real**
    `YahooFinanceAdapter`, not a hand-rolled fake provider, so the actual
    adapter-level fix is exercised end to end."""

    def __init__(self, frame_factory):
        self._frame_factory = frame_factory
        self.calls: list[tuple] = []

    def download(self, symbol, start=None, end=None, progress=None):
        self.calls.append((symbol, start, end))
        return self._frame_factory()


@pytest.fixture
def multiindex_yahoo_router():
    config = yaml.safe_load(PROVIDERS_CONFIG_PATH.read_text(encoding="utf-8"))
    client = _MultiIndexColumnYfClient(lambda: _real_yfinance_multiindex_shaped_frame())
    yahoo = YahooFinanceAdapter(client=client)
    router = ProviderRouter(providers={"yahoo_finance": yahoo}, routing_config=config)
    return router, client


def test_multiindex_columned_response_produces_real_snapshot_not_data_gap(multiindex_yahoo_router, tmp_path: Path):
    """The core P1B.4.1 regression test: reproduces the user's exact
    reported bug (route probe reports real rows, but a naive check would
    call the embedded MarketSnapshot's "No index bars available" state
    consistent with that) using a MultiIndex-columned fake yfinance
    response routed through the real YahooFinanceAdapter. After the fix,
    the route status AND the embedded MarketSnapshot must agree the data
    is real — non-empty route bars must not produce "No index bars
    available" without a documented reason."""
    router, client = multiindex_yahoo_router
    report = run_market_snapshot_smoke(
        date="2026-06-30",
        markets=["H", "US"],
        router=router,
        output_path=tmp_path / "report.json",
        gaps_path=tmp_path / "data_gaps.jsonl",
    )
    for market in ("H", "US"):
        entry = report["results"][market]
        assert entry["index_bars_rows_returned"] > 0
        assert entry["index_bars_usable"] is True
        assert entry["index_bars_status"] == "pass"
        assert entry["route_snapshot_consistency"] in ("route_pass_snapshot_pass", "route_pass_snapshot_partial")
        assert not entry["route_snapshot_consistency"].startswith("inconsistent")
        snapshot = entry["market_snapshot"]
        assert snapshot["trend_state"] != "unknown"
        assert "No index bars available" not in snapshot["summary"]
    assert len(client.calls) >= 1


class _NoCloseColumnYahoo:
    """A hand-rolled fake provider (bypassing the real adapter entirely)
    that returns real rows but with no "close" column at all — simulates
    any provider-level shape that leaves rows present but nothing usable.
    Used to prove this script's OWN status classification (not just the
    adapter-level MultiIndex fix) correctly refuses to call this "pass",
    and stays consistent with the embedded MarketSnapshot (which will
    itself be "unknown" — MarketRegimeAnalyzer requires "close")."""

    def __init__(self):
        self.calls: list[tuple] = []

    def get_daily_bars(self, symbol, market, start, end):
        self.calls.append(("daily_bars", symbol, market))
        return pd.DataFrame({"trade_date": ["20260601"] * 10, "source": ["yahoo_finance"] * 10})

    def get_index_bars(self, index_code, market, start, end):
        self.calls.append(("index_bars", index_code, market))
        return pd.DataFrame({"trade_date": ["20260601"] * 10, "source": ["yahoo_finance"] * 10})


def test_rows_without_close_column_are_not_reported_as_pass(tmp_path: Path):
    config = _load_real_providers_config()
    yahoo = _NoCloseColumnYahoo()
    router = ProviderRouter(providers={"yahoo_finance": yahoo}, routing_config=config)
    report = run_market_snapshot_smoke(
        date="2026-06-30", markets=["H"], router=router,
        output_path=tmp_path / "report.json", gaps_path=tmp_path / "data_gaps.jsonl",
    )
    entry = report["results"]["H"]
    # Real rows were returned (len(df) == 10) but with no usable "close"
    # column — must NOT be reported as "pass", and must stay consistent
    # with the embedded MarketSnapshot (which is itself "unknown").
    assert entry["index_bars_rows_returned"] == 10
    assert entry["index_bars_usable"] is False
    assert entry["index_bars_status"] != "pass"
    assert entry["market_snapshot"]["trend_state"] == "unknown"
    assert entry["route_snapshot_consistency"] == "route_fail_snapshot_unknown"
    assert entry["overall_status"] != "pass"


def test_empty_provider_result_stays_honest_and_consistency_agrees(real_router, tmp_path: Path):
    """Item 3: empty provider result remains honest unknown/data_gap, and
    the new route_snapshot_consistency field agrees (route_fail +
    snapshot unknown, never an inconsistent_* state)."""
    router, yahoo = real_router
    yahoo._raise_error = ProviderError("yfinance package is not installed")

    report = run_market_snapshot_smoke(
        date="2026-06-30", markets=["H", "US"], router=router,
        output_path=tmp_path / "report.json", gaps_path=tmp_path / "data_gaps.jsonl",
    )
    for market in ("H", "US"):
        entry = report["results"][market]
        assert entry["overall_status"] == "dependency_missing"
        assert entry["route_snapshot_consistency"] == "route_fail_snapshot_unknown"


# -- CLI exit code: deterministic, "all requested markets" semantics ------


class _MixedResultYahoo:
    """Passes for H, fails for US — used to prove the CLI exit code
    requires *every* requested market to be pass/partial, not just any
    one of them (the old `any(...)` semantics would have wrongly
    returned 0 here)."""

    def __init__(self):
        self.calls: list[tuple] = []

    def get_daily_bars(self, symbol, market, start, end):
        self.calls.append(("daily_bars", symbol, market))
        if market == "US":
            raise ProviderError("yfinance package is not installed")
        return _bars()

    def get_index_bars(self, index_code, market, start, end):
        self.calls.append(("index_bars", index_code, market))
        if market == "US":
            raise ProviderError("yfinance package is not installed")
        return _bars()


def test_cli_exit_code_zero_when_all_requested_markets_pass_or_partial(monkeypatch, tmp_path: Path):
    config = _load_real_providers_config()
    yahoo = _RecordingYahoo()
    router = ProviderRouter(providers={"yahoo_finance": yahoo}, routing_config=config)
    monkeypatch.setattr(smoke_module, "build_default_router", lambda cfg: router)

    exit_code = smoke_module.main([
        "--date", "2026-06-30", "--markets", "H,US",
        "--output", str(tmp_path / "report.json"),
        "--gaps-path", str(tmp_path / "data_gaps.jsonl"),
    ])
    assert exit_code == 0


def test_cli_exit_code_nonzero_when_all_requested_markets_fail(monkeypatch, tmp_path: Path):
    config = _load_real_providers_config()
    yahoo = _RecordingYahoo(raise_error=ProviderError("yfinance package is not installed"))
    router = ProviderRouter(providers={"yahoo_finance": yahoo}, routing_config=config)
    monkeypatch.setattr(smoke_module, "build_default_router", lambda cfg: router)

    exit_code = smoke_module.main([
        "--date", "2026-06-30", "--markets", "H,US",
        "--output", str(tmp_path / "report.json"),
        "--gaps-path", str(tmp_path / "data_gaps.jsonl"),
    ])
    assert exit_code == 1


def test_cli_exit_code_is_nonzero_when_only_some_requested_markets_pass(monkeypatch, tmp_path: Path):
    """Proves the exit policy requires ALL requested markets to be
    pass/partial — H alone would have made the old `any(...)` check
    return 0, but with US failing this must now return 1."""
    config = _load_real_providers_config()
    yahoo = _MixedResultYahoo()
    router = ProviderRouter(providers={"yahoo_finance": yahoo}, routing_config=config)
    monkeypatch.setattr(smoke_module, "build_default_router", lambda cfg: router)

    exit_code = smoke_module.main([
        "--date", "2026-06-30", "--markets", "H,US",
        "--output", str(tmp_path / "report.json"),
        "--gaps-path", str(tmp_path / "data_gaps.jsonl"),
    ])
    assert exit_code == 1

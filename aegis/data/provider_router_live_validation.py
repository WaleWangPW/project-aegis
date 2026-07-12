"""aegis/data/provider_router_live_validation.py — P1B.2.

Honest live validation for `ProviderRouter`'s H/US **secondary**
provider routes (`yahoo_finance`) — daily bars, index bars, and a
`stock_basic` not_configured/unsupported check. This module never
constructs a `TushareAdapter`, never calls `os.environ`/`.env`/
`load_dotenv`, and never requires `TUSHARE_TOKEN` — it exists
specifically to answer "does the H/US secondary route actually work"
independent of anything A股/Tushare-related (per
`docs/P1B_HUS_CRCL_PROVIDER_IMPLEMENTATION_SPEC.md` and
`Claude_Cowork_P1B2_PROVIDER_ROUTER_LIVE_VALIDATION.md`).

Status semantics (never fabricated — mirrors the vocabulary already
established by `aegis.data.coverage_report.CheckStatus` /
`aegis.data.provider_diagnostics`, extended with two P1B.2-specific
values needed for a live secondary-provider check):

- "pass": the call succeeded and returned at least one row.
- "unknown": the call succeeded but returned zero rows — does not
  confirm coverage either way (e.g. Yahoo silently swallowing a blocked
  connection into an empty frame, which is exactly what this Cowork
  sandbox does — see docs/P1B2_PROVIDER_ROUTER_LIVE_VALIDATION_RESULT.md).
  Never reported as "pass".
- "fail": the call raised a `ProviderError` that isn't recognized as a
  dependency or network problem — an unexplained real failure.
- "skipped": no sample is configured for this (market, data_type) pair.
- "not_configured": `ProviderRouter` has no route (or an unmapped H
  symbol/index) for this pair — raised structurally, before any
  provider call is attempted.
- "dependency_missing": the resolved provider's own client package
  (e.g. `yfinance`) is not installed/importable in this environment.
  Detected via `adapter.is_configured()` *before* attempting a call, so
  this never crashes and never depends on string-matching an exception.
- "network_unavailable": the call raised a `ProviderError` whose message
  looks connection/DNS/proxy/timeout related.
- "unsupported": `ProviderRouter` raised `ProviderUnsupportedError` for
  this pair (e.g. a route explicitly marked `"unsupported"`).

This module's default sample symbols reuse the same internal Aegis
codes already established in `config/providers.yaml`'s `symbol_mapping`
section (P1B.1) — `ProviderRouter` (not this module) performs the actual
symbol/index translation, so `mapped_symbol` in each check result is
computed via the router's own `SymbolMapper` for reporting only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from aegis.data.provider_router import ProviderRouter
from aegis.data.providers import ProviderError, ProviderNotConfiguredError, ProviderUnsupportedError
from aegis.data.symbol_mapping import SymbolMappingError
from aegis.data.yahoo_finance_adapter import YahooFinanceAdapter

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROVIDERS_CONFIG = REPO_ROOT / "config" / "providers.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "provider_router" / "provider_router_live_report.json"

ACCEPTED_STATUSES = (
    "pass",
    "fail",
    "unknown",
    "skipped",
    "not_configured",
    "dependency_missing",
    "network_unavailable",
    "unsupported",
)

# Internal Aegis codes — the same ones already configured in
# config/providers.yaml's symbol_mapping section (P1B.1). ProviderRouter
# (not this module) resolves these to Yahoo-style tickers.
DEFAULT_SAMPLES: dict[str, dict[str, str]] = {
    "H": {"daily_bars": "00700.HK", "index_bars": "HSI.HI"},
    "US": {"daily_bars": "CRCL", "index_bars": "SPX"},
}

# data_type -> which router method to call, keyed for stock_basic (no
# symbol argument) vs. daily_bars/index_bars (symbol/index argument).
_BARS_DATA_TYPES = ("daily_bars", "index_bars")

_NETWORK_ERROR_KEYWORDS = (
    "network",
    "connection",
    "timeout",
    "timed out",
    "resolve",
    "dns",
    "proxy",
    "unreachable",
    "refused",
    "getaddrinfo",
    "temporary failure",
    "name resolution",
)

_DEPENDENCY_ERROR_KEYWORDS = (
    "not installed",
    "no module named",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def generate_run_id() -> str:
    return f"provider_router_live_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"


def default_date_window() -> tuple[str, str]:
    """A small recent window — mirrors the "cheap probe" convention used
    elsewhere in this codebase (`aegis.data.live_validation._probe_network`)."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=30)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


@dataclass
class LiveCheckResult:
    check_name: str
    market: str
    data_type: str
    provider: str
    sample_symbol: Optional[str] = None
    mapped_symbol: Optional[str] = None
    status: str = "unknown"
    rows_returned: Optional[int] = None
    warning: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "market": self.market,
            "data_type": self.data_type,
            "provider": self.provider,
            "sample_symbol": self.sample_symbol,
            "mapped_symbol": self.mapped_symbol,
            "status": self.status,
            "rows_returned": self.rows_returned,
            "warning": self.warning,
            "error_type": self.error_type,
        }


@dataclass
class LiveValidationSummary:
    pass_count: int = 0
    fail_count: int = 0
    unknown_count: int = 0
    skipped_count: int = 0
    not_configured_count: int = 0
    dependency_missing_count: int = 0
    network_unavailable_count: int = 0
    unsupported_count: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "unknown_count": self.unknown_count,
            "skipped_count": self.skipped_count,
            "not_configured_count": self.not_configured_count,
            "dependency_missing_count": self.dependency_missing_count,
            "network_unavailable_count": self.network_unavailable_count,
            "unsupported_count": self.unsupported_count,
        }


def summarize_checks(checks: list[LiveCheckResult]) -> LiveValidationSummary:
    summary = LiveValidationSummary()
    counter_by_status = {
        "pass": "pass_count",
        "fail": "fail_count",
        "unknown": "unknown_count",
        "skipped": "skipped_count",
        "not_configured": "not_configured_count",
        "dependency_missing": "dependency_missing_count",
        "network_unavailable": "network_unavailable_count",
        "unsupported": "unsupported_count",
    }
    for check in checks:
        field_name = counter_by_status.get(check.status)
        if field_name is not None:
            setattr(summary, field_name, getattr(summary, field_name) + 1)
    return summary


def _classify_provider_error(exc: ProviderError) -> tuple[str, str]:
    """Returns (status, warning) for a `ProviderError` that wasn't one of
    the dedicated `ProviderNotConfiguredError`/`ProviderUnsupportedError`
    subclasses. Never guesses coverage — only ever downgrades an
    unexplained failure to a more specific, honest category when the
    message itself says so."""
    message = str(exc).lower()
    if any(keyword in message for keyword in _DEPENDENCY_ERROR_KEYWORDS):
        return "dependency_missing", str(exc)
    if any(keyword in message for keyword in _NETWORK_ERROR_KEYWORDS):
        return "network_unavailable", str(exc)
    return "fail", str(exc)


def _resolve_mapped_symbol(router: ProviderRouter, provider_name: str, market: str, data_type: str, sample: str) -> tuple[Optional[str], Optional[SymbolMappingError]]:
    try:
        if data_type == "daily_bars":
            return router._symbol_mapper.map_symbol(provider_name, market, sample), None
        if data_type == "index_bars":
            return router._symbol_mapper.map_index(provider_name, market, sample), None
        return None, None
    except SymbolMappingError as exc:
        return None, exc


def _run_bars_check(router: ProviderRouter, market: str, data_type: str, sample: Optional[str]) -> LiveCheckResult:
    check_name = f"{market.lower()}_{data_type}"

    if not sample:
        return LiveCheckResult(
            check_name=check_name,
            market=market,
            data_type=data_type,
            provider="unknown",
            status="skipped",
            warning="no sample symbol configured for this market/data_type",
        )

    # Resolve the route name first — never guessed, always via the same
    # ProviderRouter config every other consumer uses.
    try:
        provider_name = router._route_name(market, data_type)
    except ProviderNotConfiguredError as exc:
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider="not_configured",
            sample_symbol=sample, status="not_configured", warning=str(exc), error_type=type(exc).__name__,
        )
    except ProviderUnsupportedError as exc:
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider="unsupported",
            sample_symbol=sample, status="unsupported", warning=str(exc), error_type=type(exc).__name__,
        )

    mapped_symbol, mapping_error = _resolve_mapped_symbol(router, provider_name, market, data_type, sample)
    if mapping_error is not None:
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider=provider_name,
            sample_symbol=sample, status="not_configured", warning=str(mapping_error),
            error_type=type(mapping_error).__name__,
        )

    # Dependency check — before attempting any call, so a missing
    # package never crashes and never needs exception-message guessing.
    adapter = router._providers.get(provider_name)
    is_configured = getattr(adapter, "is_configured", None)
    if callable(is_configured) and not is_configured():
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider=provider_name,
            sample_symbol=sample, mapped_symbol=mapped_symbol, status="dependency_missing",
            warning=f"{provider_name} client/package is not available in this environment",
        )

    start, end = default_date_window()
    try:
        if data_type == "daily_bars":
            df = router.get_daily_bars(sample, market, start, end)
        else:
            df = router.get_index_bars(sample, market, start, end)
    except ProviderNotConfiguredError as exc:
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider="not_configured",
            sample_symbol=sample, mapped_symbol=mapped_symbol, status="not_configured",
            warning=str(exc), error_type=type(exc).__name__,
        )
    except ProviderUnsupportedError as exc:
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider="unsupported",
            sample_symbol=sample, mapped_symbol=mapped_symbol, status="unsupported",
            warning=str(exc), error_type=type(exc).__name__,
        )
    except ProviderError as exc:
        status, warning = _classify_provider_error(exc)
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider=provider_name,
            sample_symbol=sample, mapped_symbol=mapped_symbol, status=status,
            warning=warning, error_type=type(exc).__name__,
        )
    except Exception as exc:  # noqa: BLE001 - never crash the run; report honestly instead
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider=provider_name,
            sample_symbol=sample, mapped_symbol=mapped_symbol, status="fail",
            warning=str(exc), error_type=type(exc).__name__,
        )

    if df is None or df.empty:
        return LiveCheckResult(
            check_name=check_name, market=market, data_type=data_type, provider=provider_name,
            sample_symbol=sample, mapped_symbol=mapped_symbol, status="unknown",
            rows_returned=0, warning="call succeeded but returned zero rows — not confirmed as coverage",
        )

    return LiveCheckResult(
        check_name=check_name, market=market, data_type=data_type, provider=provider_name,
        sample_symbol=sample, mapped_symbol=mapped_symbol, status="pass", rows_returned=len(df),
    )


def _run_stock_basic_check(router: ProviderRouter, market: str) -> LiveCheckResult:
    check_name = f"{market.lower()}_stock_basic"
    try:
        router.get_stock_basic(market)
    except ProviderNotConfiguredError as exc:
        return LiveCheckResult(
            check_name=check_name, market=market, data_type="stock_basic", provider="not_configured",
            status="not_configured", warning=str(exc), error_type=type(exc).__name__,
        )
    except ProviderUnsupportedError as exc:
        return LiveCheckResult(
            check_name=check_name, market=market, data_type="stock_basic", provider="unsupported",
            status="unsupported", warning=str(exc), error_type=type(exc).__name__,
        )
    except ProviderError as exc:
        status, warning = _classify_provider_error(exc)
        return LiveCheckResult(
            check_name=check_name, market=market, data_type="stock_basic", provider="unknown",
            status=status, warning=warning, error_type=type(exc).__name__,
        )
    # It succeeded and returned something. H/US stock_basic must never
    # false-pass this check — this is the exact P1A.1 class of bug, now
    # also guarded here: a successful call for H/US on this route is
    # unexpected given config/providers.yaml, so it is reported as
    # "unknown" (a genuine surprise worth a human look), never "pass".
    return LiveCheckResult(
        check_name=check_name, market=market, data_type="stock_basic", provider="unexpected_success",
        status="unknown",
        warning="stock_basic call unexpectedly succeeded for this market — verify config/providers.yaml routing",
    )


def build_default_router(providers_config: dict, yahoo_adapter: Optional[YahooFinanceAdapter] = None) -> ProviderRouter:
    """Builds a `ProviderRouter` wired with **only** the `yahoo_finance`
    secondary provider — deliberately no Tushare instance is ever
    constructed here, so this module can never call Tushare or require
    `TUSHARE_TOKEN`, regardless of what `config/providers.yaml`'s A股
    routes say."""
    return ProviderRouter(
        providers={"yahoo_finance": yahoo_adapter or YahooFinanceAdapter()},
        routing_config=providers_config,
    )


def run_live_validation(
    *,
    markets: Optional[list[str]] = None,
    providers_config: Optional[dict] = None,
    router: Optional[ProviderRouter] = None,
    samples: Optional[dict[str, dict[str, str]]] = None,
    run_id: Optional[str] = None,
) -> dict[str, Any]:
    """Testable core behind `scripts/validate_provider_router_live.py`.
    `router` is injectable for tests (fake `yahoo_finance` adapter only —
    never a real network call from `pytest`). Never reads `.env`/
    `os.environ`; never constructs a Tushare adapter or token."""
    markets = markets if markets is not None else ["H", "US"]
    samples = samples if samples is not None else DEFAULT_SAMPLES
    run_id = run_id or generate_run_id()

    if router is None:
        if providers_config is None:
            raise ValueError("Either `router` or `providers_config` must be provided.")
        router = build_default_router(providers_config)

    checks: list[LiveCheckResult] = []
    network_attempted = False
    for market in markets:
        market_samples = samples.get(market, {})
        for data_type in _BARS_DATA_TYPES:
            result = _run_bars_check(router, market, data_type, market_samples.get(data_type))
            checks.append(result)
            if result.status not in ("skipped", "not_configured", "unsupported", "dependency_missing"):
                network_attempted = True
        checks.append(_run_stock_basic_check(router, market))

    summary = summarize_checks(checks)

    return {
        "run_id": run_id,
        "created_at": _now_iso(),
        "network_attempted": network_attempted,
        "checks": [c.to_dict() for c in checks],
        "summary": summary.to_dict(),
    }


def write_report(report: dict[str, Any], output_path: str | Path) -> None:
    import json

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

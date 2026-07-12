"""TimeTravelEngine — Phase 7 §5.3.

Replays the exact same deterministic Phase 2-4 pipeline (MarketSnapshot ->
Universe -> Signals -> ExpertCommittee -> DecisionEngine ->
RecommendationRecord) for a historical `freeze_date`, with every data read
routed through `HistoricalDataProvider` so decision-stage code can never see
data dated after `freeze_date`. After recommendations are finalized, the
context switches to `stage="evaluation"` and forward 5/10/20/40 trading-day
returns are simulated for evaluation only — those future bars never flow
back into Signal/Expert/Decision logic.

Never creates live PaperTrade/Recommendation/Review/Memory records —
nothing here writes to `data/records/`. The one on-disk side effect is
`DataGapRegistry`, which is always pointed at the isolated
`data/processed/backtests/<run_id>/data_gaps.jsonl`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from aegis.backtest.frozen_context import FrozenContext
from aegis.backtest.historical_provider import HistoricalDataProvider
from aegis.backtest.models import BacktestResult, MetricsReport
from aegis.backtest.metrics import (
    compute_action_success_rate,
    compute_average_return_by_horizon,
    compute_data_gap_count,
    compute_market_breakdown,
    compute_max_drawdown_summary,
    compute_no_future_data_violations,
    compute_sector_breakdown,
    compute_status_counts,
)
from aegis.data.cache import DataCache
from aegis.data.gaps import DataGapRegistry
from aegis.data.providers import ProviderError
from aegis.data.tushare_adapter import TushareAdapter
from aegis.decision.engine import DecisionEngine
from aegis.experts.committee import ExpertCommittee
from aegis.experts.context import AnalysisContext
from aegis.market.regime import DEFAULT_PRIMARY_INDEX, MarketSnapshotService
from aegis.market.service import MarketDataService
from aegis.models.recommendation import RecommendationRecord
from aegis.paper.metrics import compute_horizon_return, compute_max_drawdown
from aegis.portfolio.holdings_loader import HoldingLoader
from aegis.signals.base import SignalContext, compute_signals_for_candidate
from aegis.universe.builder import UniverseBuilder
from aegis.utils.dates import lookback_range, to_compact

DEFAULT_MARKETS = ["A", "H", "US"]
DEFAULT_HORIZONS = (5, 10, 20, 40)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _fetch_fundamentals(provider: Any, symbol: str, market: str, as_of: str) -> Optional[dict]:
    """Same best-effort pattern as `scripts/run_pre_market.py`'s
    `_fetch_fundamentals` — never raises, a failure/empty result just means
    `fundamentals=None` (an honest DataGap downstream, not a fabrication)."""
    try:
        df = provider.get_fundamentals(symbol, market, as_of)
    except ProviderError:
        return None
    except AttributeError:
        return None
    if df is None or df.empty:
        return None
    return df.iloc[0].to_dict()


def _iter_calendar_dates(start_date: str, end_date: str) -> list[str]:
    """Calendar-day iteration, not a real trading calendar — this project
    has no trading-calendar service yet (a known gap carried since Phase 1;
    see docs/HANDOFF.md). Non-trading days simply produce empty/DATA_GAP
    snapshots and candidates, handled gracefully by the existing Phase 2-4
    pipeline (no crash, per §9.3.6)."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    if end_dt < start_dt:
        return []
    dates = []
    current = start_dt
    while current <= end_dt:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def _add_days(date_str: str, days: int) -> str:
    return (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")


class TimeTravelEngine:
    def __init__(
        self,
        config: Optional[dict] = None,
        base_provider: Optional[Any] = None,
        data_dir: Optional[str] = None,
        repo_root: Optional[str] = None,
    ):
        self.config = config or {}
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
        self.config_dir = self.repo_root / "config"
        self.data_dir = Path(data_dir) if data_dir else self.repo_root / "data"
        self._base_provider = base_provider
        self._active_run_id: Optional[str] = None
        # Accumulates every HistoricalDataProvider.data_access_log entry
        # across calls (decision-stage and evaluation-stage alike) —
        # test-visible via `engine.access_log`, and written to
        # `data_access_log.jsonl` by scripts/run_backtest.py. Per PHASE7
        # doc §6.3: "test fails if any decision-stage access log includes
        # served data date > freeze_date" — this is the surface tests use.
        self.access_log: list[dict] = []

    @property
    def base_provider(self) -> Any:
        if self._base_provider is None:
            self._base_provider = TushareAdapter.from_env()
        return self._base_provider

    # -- run_id -----------------------------------------------------------

    def _generate_run_id(self) -> str:
        return f"bt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"

    def _resolve_run_id(self, run_id: Optional[str]) -> str:
        if run_id:
            return run_id
        if self._active_run_id:
            return self._active_run_id
        return self._generate_run_id()

    # -- public API (PHASE7 doc §5.3) -------------------------------------

    def run_date(
        self,
        freeze_date: str,
        session: str = "close",
        markets: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> BacktestResult:
        run_id = self._resolve_run_id(run_id)
        markets = markets if markets is not None else DEFAULT_MARKETS
        output_dir = self.data_dir / "processed" / "backtests" / run_id

        gaps = DataGapRegistry(output_dir / "data_gaps.jsonl")
        gaps_before = len(gaps.list_gaps())

        universe_cfg = _load_yaml(self.config_dir / "universe.yaml")
        experts_cfg = _load_yaml(self.config_dir / "experts.yaml")
        decision_cfg = _load_yaml(self.config_dir / "decision_rules.yaml")
        lookback_days = universe_cfg.get("default", {}).get("lookback_days", 120)

        holdings = HoldingLoader(self.config_dir / "holdings.yaml").load_holdings()
        holdings_by_key = {(h.market, h.symbol): h for h in holdings}

        frozen_context = FrozenContext(freeze_date=freeze_date, session=session, markets=markets, stage="decision")
        historical_provider = HistoricalDataProvider(self.base_provider, frozen_context, gaps=gaps)
        market_data_service = MarketDataService(provider=historical_provider, cache=None, gaps=gaps)

        snapshot_service = MarketSnapshotService(
            market_data_service=market_data_service, gaps=gaps, lookback_days=lookback_days
        )
        snapshots = snapshot_service.build_snapshots(date=freeze_date, session=session, markets=markets)
        snapshot_by_market = {s.market: s for s in snapshots}

        universe_builder = UniverseBuilder(provider=historical_provider, config=universe_cfg, gaps=gaps)
        candidates = universe_builder.build_candidates(
            date=freeze_date, session=session, markets=markets, holdings=holdings, market_snapshots=snapshots
        )

        recommendations = self._run_decision_pipeline(
            candidates=candidates,
            holdings_by_key=holdings_by_key,
            snapshot_by_market=snapshot_by_market,
            market_data_service=market_data_service,
            historical_provider=historical_provider,
            freeze_date=freeze_date,
            session=session,
            lookback_days=lookback_days,
            experts_cfg=experts_cfg,
            decision_cfg=decision_cfg,
        )

        no_future_data_violations = historical_provider.violations
        data_gaps_this_run = gaps.list_gaps()[gaps_before:]
        self.access_log.extend(historical_provider.data_access_log)

        interim = BacktestResult(
            run_id=run_id,
            freeze_date=freeze_date,
            session=session,
            markets=markets,
            market_snapshot_ids=[s.snapshot_id for s in snapshots],
            candidate_count=len(candidates),
            recommendation_ids=[r.recommendation_id for r in recommendations],
            recommendations=[r.model_dump() for r in recommendations],
            forward_returns={},
            data_gaps=data_gaps_this_run,
            no_future_data_violations=no_future_data_violations,
            created_at=_now_iso(),
        )
        return self.simulate_future_returns(interim)

    def run_range(
        self,
        start_date: str,
        end_date: str,
        session: str = "close",
        markets: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> list[BacktestResult]:
        markets = markets if markets is not None else DEFAULT_MARKETS
        resolved_run_id = self._resolve_run_id(run_id)
        previous_active = self._active_run_id
        self._active_run_id = resolved_run_id
        try:
            results = [
                self.run_date(freeze_date=date_str, session=session, markets=markets, run_id=resolved_run_id)
                for date_str in _iter_calendar_dates(start_date, end_date)
            ]
        finally:
            self._active_run_id = previous_active
        return results

    def simulate_future_returns(
        self, result: BacktestResult, horizons: tuple[int, ...] = DEFAULT_HORIZONS
    ) -> BacktestResult:
        """Public/independently-testable per PHASE7 doc §5.3 — builds a
        fresh `stage="evaluation"` `HistoricalDataProvider` (never reusing
        a decision-stage one) and fills in `forward_returns` for every
        recommendation already present on `result`. Never mutates
        Signal/Expert/Decision state — this only ever produces evaluation
        metadata alongside an already-finalized `BacktestResult`."""
        frozen_context = FrozenContext(
            freeze_date=result.freeze_date, session=result.session, markets=result.markets, stage="evaluation"
        )
        historical_provider = HistoricalDataProvider(self.base_provider, frozen_context)

        freeze_compact = to_compact(result.freeze_date)
        window_end_compact = to_compact(_add_days(result.freeze_date, 90))

        forward_returns: dict[str, dict] = {}
        for rec in result.recommendations:
            bars = historical_provider.get_future_bars_for_evaluation(
                rec["symbol"], rec["market"], freeze_compact, window_end_compact
            )
            forward_returns[rec["recommendation_id"]] = self._forward_return_entry(
                bars, freeze_compact, horizons
            )

        self.access_log.extend(historical_provider.data_access_log)
        return result.model_copy(update={"forward_returns": forward_returns})

    def build_metrics_report(self, results: list[BacktestResult]) -> MetricsReport:
        run_id = results[0].run_id if results else self._generate_run_id()
        start_date = min((r.freeze_date for r in results), default="")
        end_date = max((r.freeze_date for r in results), default="")

        status_counts = compute_status_counts(results)
        total_recommendations = sum(status_counts.values())
        data_gap_count = compute_data_gap_count(results)
        violations = compute_no_future_data_violations(results)

        summary = (
            f"{len(results)} trading day(s) processed from {start_date} to {end_date}; "
            f"{total_recommendations} recommendation(s) "
            f"(Action={status_counts['Action']}, Ready={status_counts['Ready']}, "
            f"Watch={status_counts['Watch']}, Exit={status_counts['Exit']}); "
            f"{data_gap_count} data gap(s); {violations} no-future-data violation(s)."
        )

        return MetricsReport(
            run_id=run_id,
            start_date=start_date,
            end_date=end_date,
            trading_days_run=len(results),
            total_recommendations=total_recommendations,
            action_count=status_counts["Action"],
            ready_count=status_counts["Ready"],
            watch_count=status_counts["Watch"],
            exit_count=status_counts["Exit"],
            action_success_rate_5d=compute_action_success_rate(results, "5d"),
            action_success_rate_10d=compute_action_success_rate(results, "10d"),
            action_success_rate_20d=compute_action_success_rate(results, "20d"),
            action_success_rate_40d=compute_action_success_rate(results, "40d"),
            average_return_by_horizon=compute_average_return_by_horizon(results),
            max_drawdown_summary=compute_max_drawdown_summary(results),
            market_breakdown=compute_market_breakdown(results),
            sector_breakdown=compute_sector_breakdown(results),
            data_gap_count=data_gap_count,
            no_future_data_violations=violations,
            summary=summary,
            created_at=_now_iso(),
        )

    # -- internals ---------------------------------------------------------

    def _run_decision_pipeline(
        self,
        *,
        candidates,
        holdings_by_key,
        snapshot_by_market,
        market_data_service,
        historical_provider,
        freeze_date,
        session,
        lookback_days,
        experts_cfg,
        decision_cfg,
    ) -> list[RecommendationRecord]:
        start, end = lookback_range(freeze_date, lookback_days)
        committee = ExpertCommittee(config=experts_cfg)
        engine = DecisionEngine()

        recommendations: list[RecommendationRecord] = []
        for candidate in candidates:
            bars = market_data_service.get_daily_bars_cached(candidate.symbol, candidate.market, start, end)
            index_code = DEFAULT_PRIMARY_INDEX.get(candidate.market)
            index_bars = (
                market_data_service.get_index_bars_cached(index_code, candidate.market, start, end)
                if index_code
                else None
            )
            fundamentals = _fetch_fundamentals(historical_provider, candidate.symbol, candidate.market, freeze_date)

            signal_context = SignalContext(
                date=freeze_date,
                session=session,
                symbol=candidate.symbol,
                market=candidate.market,
                bars=bars if bars is not None and not bars.empty else None,
                index_bars=index_bars if index_bars is not None and not index_bars.empty else None,
                sector_bars=None,
                fundamentals=fundamentals,
                candidate=candidate,
                market_snapshot=snapshot_by_market.get(candidate.market),
                data_quality=candidate.data_quality,
            )
            candidate_signals = compute_signals_for_candidate(signal_context)

            holding = holdings_by_key.get((candidate.market, candidate.symbol))
            analysis_context = AnalysisContext(
                date=freeze_date,
                session=session,
                candidate=candidate,
                market_snapshot=snapshot_by_market.get(candidate.market),
                holding=holding,
                signals=candidate_signals,
                portfolio_snapshot=None,
                data_gaps=[],
                config=experts_cfg,
            )
            candidate_opinions = committee.analyze_candidate(analysis_context)

            market_snapshot = snapshot_by_market.get(candidate.market)
            if market_snapshot is not None:
                _decision, recommendation = engine.decide(
                    market_snapshot=market_snapshot,
                    candidate=candidate,
                    expert_opinions=candidate_opinions,
                    holding=holding,
                    config=decision_cfg,
                )
                recommendations.append(recommendation)

        return recommendations

    def _forward_return_entry(self, bars, freeze_compact: str, horizons: tuple[int, ...]) -> dict:
        empty_entry: dict = {f"{h}d": None for h in horizons}
        empty_entry.update({"max_drawdown": None, "status": "data_gap"})

        if bars is None or bars.empty or "trade_date" not in bars.columns or "close" not in bars.columns:
            return empty_entry

        sorted_bars = bars.sort_values("trade_date")
        entry_rows = sorted_bars[sorted_bars["trade_date"].astype(str) == freeze_compact]
        if entry_rows.empty:
            return empty_entry

        entry_price = float(entry_rows.iloc[0]["close"])
        post_entry = sorted_bars[sorted_bars["trade_date"].astype(str) > freeze_compact]
        closes_after = [float(c) for c in post_entry["close"].tolist()]

        entry: dict = {}
        for horizon in horizons:
            entry[f"{horizon}d"] = (
                compute_horizon_return(entry_price, closes_after[horizon - 1])
                if len(closes_after) >= horizon
                else None
            )
        entry["max_drawdown"] = compute_max_drawdown([entry_price] + closes_after)
        entry["status"] = "complete"
        return entry

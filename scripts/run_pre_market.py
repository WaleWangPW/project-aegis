#!/usr/bin/env python3
"""run_pre_market.py — Phase 2/3/4/5/6 pre-market pipeline (P1D.2 update).

P1D.2: wires a ProviderRouter (TushareAdapter for A + YahooFinanceAdapter for
H/US) into the MarketDataService so that H/US holdings/candidates receive real
daily/index bars when Yahoo Finance is locally available. The injectable
`provider_router` parameter allows tests to supply a fake router without any
real network calls. This file still never reads `.env`/tokens directly —
`TushareAdapter.from_env()` reads from the environment on the user's machine,
same as before; the new YahooFinanceAdapter() below reads no secret at all.


Phase 2: load config -> load holdings -> build MarketSnapshot -> build
Universe/Candidates -> write processed artifacts -> print summary.

Phase 3 adds: compute Signals per candidate -> run the Expert Committee ->
write Signal/ExpertOpinion artifacts.

Phase 4 adds: run the Decision Engine per candidate -> build
RecommendationRecord -> persist DecisionRecord + RecommendationRecord.

Phase 5 adds: build the Dashboard JSON (`data/dashboard/dashboard_data.json`)
from the just-persisted MarketSnapshot/RecommendationRecord records.

Phase 6 adds: for every freshly-generated `Action` recommendation, try to
open a virtual `PaperTrade` via `PaperTradeService` (never a real order) ->
STOP. It does NOT run Review or a Backtest here — updating open trades'
forward returns, generating due reviews, and appending InvestmentMemory
lessons is `scripts/run_close.py`'s job (a separate, later pipeline stage),
not this pre-market script's. If PaperTrade creation or the dashboard build
fails, the error is recorded on the result and reported clearly, but it
never hides or discards the already-computed recommendation results.

Usage:
    python scripts/run_pre_market.py --date 2026-07-03
    python scripts/run_pre_market.py --date 2026-07-03 --markets A,H,US
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.dashboard.builder import DashboardBuilder  # noqa: E402
from aegis.data.cache import DataCache  # noqa: E402
from aegis.data.gaps import DataGapRegistry  # noqa: E402
from aegis.data.provider_router import ProviderRouter  # noqa: E402
from aegis.data.providers import ProviderError  # noqa: E402
from aegis.data.tushare_adapter import TushareAdapter  # noqa: E402
from aegis.data.yahoo_finance_adapter import YahooFinanceAdapter  # noqa: E402
from aegis.decision.engine import DecisionEngine  # noqa: E402
from aegis.experts.committee import ExpertCommittee  # noqa: E402
from aegis.experts.context import AnalysisContext  # noqa: E402
from aegis.market.regime import DEFAULT_PRIMARY_INDEX, MarketSnapshotService  # noqa: E402
from aegis.market.service import MarketDataService  # noqa: E402
from aegis.models.candidate import Candidate  # noqa: E402
from aegis.models.decision import DecisionRecord  # noqa: E402
from aegis.models.expert_opinion import ExpertOpinion  # noqa: E402
from aegis.models.holding import Holding  # noqa: E402
from aegis.models.market_snapshot import MarketSnapshot  # noqa: E402
from aegis.models.recommendation import RecommendationRecord  # noqa: E402
from aegis.models.paper_trade import PaperTrade  # noqa: E402
from aegis.models.signal import Signal  # noqa: E402
from aegis.paper.repository import PaperTradeRepository  # noqa: E402
from aegis.paper.service import PaperTradeService  # noqa: E402
from aegis.portfolio.holdings_loader import HoldingLoader  # noqa: E402
from aegis.recommendation.repository import RecommendationRepository  # noqa: E402
from aegis.signals.base import SignalContext, compute_signals_for_candidate  # noqa: E402
from aegis.universe.builder import UniverseBuilder  # noqa: E402
from aegis.utils.dates import lookback_range  # noqa: E402
from aegis.utils.jsonl import append_jsonl  # noqa: E402

DEFAULT_MARKETS = ["A", "H", "US"]


def _build_provider_router(config_dir: Path, tushare_adapter: Any) -> ProviderRouter:
    """Build a ProviderRouter wired with TushareAdapter (A股 daily/index) and
    YahooFinanceAdapter (H/US daily/index), using the repo's providers.yaml
    routing config.

    Called only when no `provider_router` is injected from outside. Never reads
    `.env` or any token — TushareAdapter is already constructed by the caller
    (from_env() already ran); YahooFinanceAdapter requires no secret.
    """
    providers_config_path = config_dir / "providers.yaml"
    providers_config: dict = {}
    if providers_config_path.exists():
        providers_config = _load_yaml(providers_config_path)
    return ProviderRouter(
        providers={
            "tushare": tushare_adapter,
            "yahoo_finance": YahooFinanceAdapter(),
        },
        routing_config=providers_config,
    )


@dataclass
class PreMarketResult:
    date: str
    markets: list[str]
    market_snapshots: list[MarketSnapshot]
    candidates: list[Candidate]
    forced_holdings: int
    data_gaps: int
    signals: list[Signal] = field(default_factory=list)
    expert_opinions: list[ExpertOpinion] = field(default_factory=list)
    decisions: list[DecisionRecord] = field(default_factory=list)
    recommendations: list[RecommendationRecord] = field(default_factory=list)
    paper_trades_created: list[PaperTrade] = field(default_factory=list)
    paper_trade_error: Optional[str] = None
    dashboard_path: Optional[Path] = None
    dashboard_error: Optional[str] = None

    @property
    def status_counts(self) -> dict[str, int]:
        return dict(Counter(r.status for r in self.recommendations))


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _fetch_fundamentals(provider: Any, symbol: str, market: str, as_of: str) -> Optional[dict]:
    """Best-effort fundamentals lookup. Never raises — a provider failure or
    empty result just means `fundamentals=None`, which FundamentalSignal
    already treats as a DataGap (unknown), not a fabricated value."""
    try:
        df = provider.get_fundamentals(symbol, market, as_of)
    except ProviderError:
        return None
    except AttributeError:
        # provider doesn't implement get_fundamentals (e.g. a minimal fake
        # used only for index/stock_basic in tests) — treat as missing.
        return None
    if df is None or df.empty:
        return None
    return df.iloc[0].to_dict()


def run_pre_market(
    *,
    date: str,
    markets: Optional[list[str]] = None,
    repo_root: Optional[Path] = None,
    provider: Optional[Any] = None,
    provider_router: Optional[Any] = None,
) -> PreMarketResult:
    """Testable core logic behind the CLI.

    `provider` — injectable Tushare-compatible adapter (A股). If omitted,
    TushareAdapter.from_env() is used, which degrades to DataGaps when no
    token is configured and never fabricates data.

    `provider_router` — injectable ProviderRouter for H/US daily/index bars.
    If omitted, _build_provider_router() constructs one using TushareAdapter
    (A stock_basic/daily) + YahooFinanceAdapter (H/US daily/index).  Tests
    may supply a fake router here to avoid real network calls.
    """
    # Note: an explicit empty list means "no markets" and must be respected
    # (e.g. §11.6's "handle empty candidates cleanly" test) — only fall
    # back to the default when markets is omitted entirely (None).
    markets = markets if markets is not None else DEFAULT_MARKETS
    root = repo_root or Path(__file__).resolve().parents[1]
    config_dir = root / "config"
    data_dir = root / "data"

    universe_cfg = _load_yaml(config_dir / "universe.yaml")
    experts_cfg = _load_yaml(config_dir / "experts.yaml")
    decision_cfg = _load_yaml(config_dir / "decision_rules.yaml")
    lookback_days = universe_cfg.get("default", {}).get("lookback_days", 120)

    holdings = HoldingLoader(config_dir / "holdings.yaml").load_holdings()
    holdings_by_key = {(h.market, h.symbol): h for h in holdings}

    adapter = provider if provider is not None else TushareAdapter.from_env()
    cache = DataCache(data_dir / "cache")
    gaps_path = data_dir / "records" / "data_gaps.jsonl"
    gaps = DataGapRegistry(gaps_path)
    gaps_before = len(gaps.list_gaps())

    # P1D.2: use a ProviderRouter so H/US daily/index bars go through
    # YahooFinanceAdapter rather than TushareAdapter (which only handles A股).
    # An injected `provider_router` is used as-is (tests supply fakes here).
    effective_router = (
        provider_router
        if provider_router is not None
        else _build_provider_router(config_dir, adapter)
    )
    market_data_service = MarketDataService(provider_router=effective_router, cache=cache, gaps=gaps)
    snapshot_service = MarketSnapshotService(
        market_data_service=market_data_service,
        gaps=gaps,
        lookback_days=lookback_days,
    )
    snapshots = snapshot_service.build_snapshots(date=date, session="pre_market", markets=markets)
    snapshot_by_market = {s.market: s for s in snapshots}

    universe_builder = UniverseBuilder(provider=adapter, config=universe_cfg, gaps=gaps)
    candidates = universe_builder.build_candidates(
        date=date,
        session="pre_market",
        markets=markets,
        holdings=holdings,
        market_snapshots=snapshots,
    )

    signals, opinions, decisions, recommendations = _run_pipeline_per_candidate(
        candidates=candidates,
        holdings_by_key=holdings_by_key,
        snapshot_by_market=snapshot_by_market,
        market_data_service=market_data_service,
        provider=adapter,
        date=date,
        session="pre_market",
        lookback_days=lookback_days,
        experts_cfg=experts_cfg,
        decision_cfg=decision_cfg,
    )

    _persist(data_dir, date, snapshots, candidates, signals, opinions, decisions, recommendations)

    # Phase 6: try to open a virtual PaperTrade for every freshly-generated
    # Action recommendation. Never a real order (Master Spec §4/ADR-004);
    # Ready/Watch/Exit never create one (PaperTradeService itself enforces
    # this). A creation failure (e.g. an unexpected exception from the data
    # provider) is reported on the result, never allowed to hide or discard
    # the already-computed/persisted recommendations.
    paper_trades_created: list[PaperTrade] = []
    paper_trade_error: Optional[str] = None
    try:
        paper_repository = PaperTradeRepository(data_dir / "records")
        paper_trade_service = PaperTradeService(
            repository=paper_repository, market_data_service=market_data_service, gaps=gaps
        )
        for recommendation in recommendations:
            trade = paper_trade_service.create_trade_from_recommendation(recommendation)
            if trade is not None:
                paper_trades_created.append(trade)
    except Exception as exc:  # noqa: BLE001 - deliberate, reported on the result
        paper_trade_error = f"{type(exc).__name__}: {exc}"

    # Dashboard JSON is built from the records just persisted above (it
    # reads recommendations.jsonl/market_snapshots.jsonl back, same as a
    # standalone `scripts/build_dashboard.py` run would). A dashboard build
    # failure is reported on the result, not swallowed and not allowed to
    # discard the recommendation results already computed.
    dashboard_path: Optional[Path] = None
    dashboard_error: Optional[str] = None
    try:
        dashboard_builder = DashboardBuilder(
            records_dir=data_dir / "records",
            holdings_config_path=config_dir / "holdings.yaml",
            output_path=data_dir / "dashboard" / "dashboard_data.json",
        )
        dashboard_payload = dashboard_builder.build(date=date, session="pre_market")
        dashboard_path = dashboard_builder.write_json(dashboard_payload)
    except Exception as exc:  # noqa: BLE001 - deliberate, reported on the result
        dashboard_error = f"{type(exc).__name__}: {exc}"

    forced_holdings = sum(1 for c in candidates if c.source == "holding")
    data_gaps_delta = len(gaps.list_gaps()) - gaps_before

    return PreMarketResult(
        date=date,
        markets=markets,
        market_snapshots=snapshots,
        candidates=candidates,
        forced_holdings=forced_holdings,
        data_gaps=data_gaps_delta,
        signals=signals,
        expert_opinions=opinions,
        decisions=decisions,
        recommendations=recommendations,
        paper_trades_created=paper_trades_created,
        paper_trade_error=paper_trade_error,
        dashboard_path=dashboard_path,
        dashboard_error=dashboard_error,
    )


def _run_pipeline_per_candidate(
    *,
    candidates: list[Candidate],
    holdings_by_key: dict[tuple[str, str], Holding],
    snapshot_by_market: dict[str, MarketSnapshot],
    market_data_service: MarketDataService,
    provider: Any,
    date: str,
    session: str,
    lookback_days: int,
    experts_cfg: dict,
    decision_cfg: dict,
) -> tuple[list[Signal], list[ExpertOpinion], list[DecisionRecord], list[RecommendationRecord]]:
    start, end = lookback_range(date, lookback_days)
    committee = ExpertCommittee(config=experts_cfg)
    engine = DecisionEngine()

    all_signals: list[Signal] = []
    all_opinions: list[ExpertOpinion] = []
    all_decisions: list[DecisionRecord] = []
    all_recommendations: list[RecommendationRecord] = []

    for candidate in candidates:
        bars = market_data_service.get_daily_bars_cached(candidate.symbol, candidate.market, start, end)
        index_code = DEFAULT_PRIMARY_INDEX.get(candidate.market)
        index_bars = (
            market_data_service.get_index_bars_cached(index_code, candidate.market, start, end)
            if index_code
            else None
        )
        fundamentals = _fetch_fundamentals(provider, candidate.symbol, candidate.market, date)

        signal_context = SignalContext(
            date=date,
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
        all_signals.extend(candidate_signals)

        holding = holdings_by_key.get((candidate.market, candidate.symbol))
        analysis_context = AnalysisContext(
            date=date,
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
        all_opinions.extend(candidate_opinions)

        market_snapshot = snapshot_by_market.get(candidate.market)
        if market_snapshot is not None:
            decision, recommendation = engine.decide(
                market_snapshot=market_snapshot,
                candidate=candidate,
                expert_opinions=candidate_opinions,
                holding=holding,
                config=decision_cfg,
            )
            all_decisions.append(decision)
            all_recommendations.append(recommendation)
        # If there is genuinely no MarketSnapshot at all for this market
        # (should not happen — MarketSnapshotService always returns one
        # per requested market, possibly "unknown"), we skip Decision/
        # Recommendation for that candidate rather than fabricate one.

    return all_signals, all_opinions, all_decisions, all_recommendations


def _persist(
    data_dir: Path,
    date: str,
    snapshots: list[MarketSnapshot],
    candidates: list[Candidate],
    signals: list[Signal],
    opinions: list[ExpertOpinion],
    decisions: list[DecisionRecord],
    recommendations: list[RecommendationRecord],
) -> None:
    records_dir = data_dir / "records"
    for snap in snapshots:
        append_jsonl(records_dir / "market_snapshots.jsonl", snap.model_dump())
    for cand in candidates:
        append_jsonl(records_dir / "candidates.jsonl", cand.model_dump())
    for sig in signals:
        append_jsonl(records_dir / "signals.jsonl", sig.model_dump())
    for opinion in opinions:
        append_jsonl(records_dir / "expert_opinions.jsonl", opinion.model_dump())

    repository = RecommendationRepository(records_dir)
    for decision in decisions:
        repository.append_decision(decision)
    for recommendation in recommendations:
        repository.append_recommendation(recommendation)

    processed_dir = data_dir / "processed" / date
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "market_snapshots_pre_market.json").write_text(
        json.dumps([s.model_dump() for s in snapshots], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (processed_dir / "candidates_pre_market.json").write_text(
        json.dumps([c.model_dump() for c in candidates], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (processed_dir / "signals_pre_market.json").write_text(
        json.dumps([s.model_dump() for s in signals], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (processed_dir / "expert_opinions_pre_market.json").write_text(
        json.dumps([o.model_dump() for o in opinions], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (processed_dir / "decisions_pre_market.json").write_text(
        json.dumps([d.model_dump() for d in decisions], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (processed_dir / "recommendations_pre_market.json").write_text(
        json.dumps([r.model_dump() for r in recommendations], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _print_summary(result: PreMarketResult) -> None:
    print("Project Aegis pre-market Phase 6")
    print(f"date: {result.date}")
    print(f"markets: {','.join(result.markets)}")
    print(f"market_snapshots: {len(result.market_snapshots)}")
    print(f"candidates: {len(result.candidates)}")
    print(f"forced_holdings: {result.forced_holdings}")
    print(f"data_gaps: {result.data_gaps}")
    print(f"signals: {len(result.signals)}")
    print(f"expert_opinions: {len(result.expert_opinions)}")
    print(f"decisions: {len(result.decisions)}")
    print(f"recommendations: {len(result.recommendations)}")
    counts = result.status_counts
    print(
        "statuses: "
        f"Watch={counts.get('Watch', 0)}, Ready={counts.get('Ready', 0)}, "
        f"Action={counts.get('Action', 0)}, Exit={counts.get('Exit', 0)}"
    )
    if not result.recommendations:
        print("No recommendations were generated (no candidates, or no market data available).")
    if result.paper_trade_error:
        print(f"paper_trades_created: FAILED ({result.paper_trade_error})")
    else:
        print(f"paper_trades_created: {len(result.paper_trades_created)}")
    if result.dashboard_error:
        print(f"dashboard_build: FAILED ({result.dashboard_error})")
    elif result.dashboard_path is not None:
        print(f"dashboard_build: {result.dashboard_path}")
    print("Phase 6 pre-market step complete. Run scripts/run_close.py for Paper Trade updates + Review + Memory. No Time Travel Backtest generated in this phase.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Project Aegis Phase 6 pre-market pipeline.")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--markets", default="A,H,US", help="Comma-separated, e.g. A,H,US")
    args = parser.parse_args(argv)

    markets = [m.strip() for m in args.markets.split(",") if m.strip()]
    result = run_pre_market(date=args.date, markets=markets)
    _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

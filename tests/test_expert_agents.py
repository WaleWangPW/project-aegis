"""Phase 3 tests for the 7 P0 Expert Agents — PHASE3 doc §9.3.

Signals here are hand-built `Signal` fixtures (not run through the real
Signal Library) so each agent's stance rule can be tested in isolation and
deterministically.
"""

from __future__ import annotations

from aegis.experts.capital_flow import CapitalFlowAgent
from aegis.experts.context import AnalysisContext
from aegis.experts.fundamental import FundamentalAgent
from aegis.experts.market_regime import MarketRegimeAgent
from aegis.experts.risk import RiskAgent
from aegis.experts.sector import SectorAgent
from aegis.experts.timing import TimingAgent
from aegis.experts.trend import TrendAgent
from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.models.expert_opinion import ExpertOpinion
from aegis.models.market_snapshot import IndexSummary, MarketSnapshot
from aegis.models.signal import Signal

ALL_AGENTS = [
    MarketRegimeAgent(),
    TrendAgent(),
    FundamentalAgent(),
    CapitalFlowAgent(),
    SectorAgent(),
    TimingAgent(),
    RiskAgent(),
]

ALLOWED_STANCES = {"support", "oppose", "neutral", "veto"}
FORBIDDEN_STATUSES = {"Watch", "Ready", "Action", "Exit"}


def _candidate(sector="Fintech", liquidity_ok=True, dq_status="complete") -> Candidate:
    return Candidate(
        candidate_id="cand_20260703_US_AAA",
        symbol="AAA",
        market="US",
        sector=sector,
        source="universe_builder",
        filter_reason=["liquidity_ok"],
        liquidity_ok=liquidity_ok,
        data_quality=DataQuality(status=dq_status),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _snapshot(trend="uptrend", liquidity="normal", risk="low", sentiment="risk_on", sector_rotation=None) -> MarketSnapshot:
    return MarketSnapshot(
        snapshot_id="mkt_20260703_US_pre_market",
        date="2026-07-03",
        session="pre_market",
        market="US",
        index_summary=IndexSummary(primary_index="SPX", primary_index_change_pct=0.01),
        trend_state=trend,
        liquidity_state=liquidity,
        sentiment_state=sentiment,
        sector_rotation=sector_rotation or [],
        risk_level=risk,
        summary="test snapshot",
        data_quality=DataQuality(status="complete"),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _signal(name, signal_type, value, evidence_strength="moderate") -> Signal:
    return Signal(
        signal_id=f"sig_20260703_US_AAA_{name}",
        signal_name=name,
        signal_type=signal_type,
        symbol="AAA",
        market="US",
        date="2026-07-03",
        value=value,
        interpretation="fixture signal",
        evidence_strength=evidence_strength,
        data_source="tushare",
    )


def _bullish_signals() -> list[Signal]:
    return [
        _signal("trend_ma_alignment", "trend", {"direction": "uptrend", "recent_return": 0.05}, "strong"),
        _signal("volume_expansion", "volume", {"state": "expansion"}, "moderate"),
        _signal("relative_strength_vs_index", "relative_strength", {"relative_strength": 0.02}, "moderate"),
        _signal("sector_rotation_presence", "sector", {"in_rotation": True}, "moderate"),
        _signal("fundamental_presence", "fundamental", {"risk_flags": []}, "weak"),
        _signal("risk_volatility_drawdown", "risk", {"flags": []}, "weak"),
    ]


def _bearish_signals() -> list[Signal]:
    return [
        _signal("trend_ma_alignment", "trend", {"direction": "downtrend", "recent_return": -0.05}, "strong"),
        _signal("volume_expansion", "volume", {"state": "contraction"}, "moderate"),
        _signal("relative_strength_vs_index", "relative_strength", {"relative_strength": -0.03}, "moderate"),
        _signal("sector_rotation_presence", "sector", {"in_rotation": False}, "moderate"),
        _signal("fundamental_presence", "fundamental", {"risk_flags": ["debt_high"]}, "weak"),
        _signal("risk_volatility_drawdown", "risk", {"flags": ["high_volatility"]}, "moderate"),
    ]


def test_every_p0_agent_returns_valid_expert_opinion():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(),
        market_snapshot=_snapshot(), signals=_bullish_signals(),
    )
    for agent in ALL_AGENTS:
        opinion = agent.analyze(context)
        assert isinstance(opinion, ExpertOpinion)
        assert opinion.stance in ALLOWED_STANCES
        assert opinion.recommendation_id == context.provisional_recommendation_id
        assert opinion.expert_name == agent.name


def test_support_stances_are_deterministic_from_bullish_fixture():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(),
        market_snapshot=_snapshot(trend="uptrend", liquidity="normal", risk="low", sentiment="risk_on", sector_rotation=["Fintech"]),
        signals=_bullish_signals(),
    )
    stances = {agent.name: agent.analyze(context).stance for agent in ALL_AGENTS}

    assert stances["MarketRegimeAgent"] == "support"
    assert stances["TrendAgent"] == "support"
    assert stances["FundamentalAgent"] == "support"
    assert stances["CapitalFlowAgent"] == "support"
    assert stances["SectorAgent"] == "support"
    assert stances["TimingAgent"] == "support"
    assert stances["RiskAgent"] == "support"


def test_oppose_stances_are_deterministic_from_bearish_fixture():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(),
        market_snapshot=_snapshot(trend="downtrend", liquidity="weak", risk="high", sentiment="risk_off", sector_rotation=["Energy"]),
        signals=_bearish_signals(),
    )
    stances = {agent.name: agent.analyze(context).stance for agent in ALL_AGENTS}

    assert stances["MarketRegimeAgent"] == "oppose"
    assert stances["TrendAgent"] == "oppose"
    assert stances["FundamentalAgent"] == "oppose"
    assert stances["CapitalFlowAgent"] == "oppose"
    assert stances["SectorAgent"] == "oppose"
    assert stances["TimingAgent"] == "oppose"
    assert stances["RiskAgent"] == "oppose"


def test_missing_data_is_propagated_into_missing_data_field():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(sector=None),
        market_snapshot=None, signals=[],
    )
    for agent in ALL_AGENTS:
        opinion = agent.analyze(context)
        assert opinion.stance == "neutral" or opinion.stance == "veto"
        assert len(opinion.missing_data) > 0


def test_no_agent_emits_watch_ready_action_exit_status():
    context = AnalysisContext(
        date="2026-07-03", session="pre_market", candidate=_candidate(),
        market_snapshot=_snapshot(), signals=_bullish_signals(),
    )
    for agent in ALL_AGENTS:
        opinion = agent.analyze(context)
        assert opinion.stance not in FORBIDDEN_STATUSES
        # ExpertOpinion has no status/action_label/price_target fields at all.
        assert not hasattr(opinion, "status")
        assert not hasattr(opinion, "action_label")

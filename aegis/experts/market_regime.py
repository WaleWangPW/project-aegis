"""MarketRegimeAgent — Phase 3 §7.2.

Reads the MarketSnapshot only — no signals. Never emits veto (RiskAgent
owns veto in P0).
"""

from __future__ import annotations

from aegis.experts.base import BaseExpertAgent
from aegis.experts.context import AnalysisContext
from aegis.models.expert_opinion import ExpertOpinion

_UNFAVORABLE_LIQUIDITY = {"weak"}
_FAVORABLE_LIQUIDITY = {"normal", "strong"}
_FAVORABLE_RISK = {"low", "medium"}


class MarketRegimeAgent(BaseExpertAgent):
    name = "MarketRegimeAgent"

    def analyze(self, context: AnalysisContext) -> ExpertOpinion:
        snap = context.market_snapshot
        if snap is None:
            return self._neutral(context, missing_data=["market_snapshot"], summary="No MarketSnapshot available for this market/session.")

        unknown_fields = [
            field_name
            for field_name, value in (
                ("trend_state", snap.trend_state),
                ("liquidity_state", snap.liquidity_state),
                ("risk_level", snap.risk_level),
            )
            if value == "unknown"
        ]
        if unknown_fields:
            return self._neutral(
                context,
                missing_data=unknown_fields,
                evidence=[f"market_snapshot:{snap.snapshot_id}"],
                summary=f"MarketSnapshot has unknown state(s): {', '.join(unknown_fields)}.",
            )

        evidence = [
            f"market_snapshot:{snap.snapshot_id}",
            f"trend_state={snap.trend_state}",
            f"liquidity_state={snap.liquidity_state}",
            f"risk_level={snap.risk_level}",
        ]

        if snap.trend_state == "downtrend" or snap.liquidity_state in _UNFAVORABLE_LIQUIDITY or snap.risk_level == "high":
            return self._opinion(
                context,
                stance="oppose",
                confidence=0.65,
                evidence=evidence,
                risks=[f"market_trend={snap.trend_state}", f"market_liquidity={snap.liquidity_state}", f"market_risk={snap.risk_level}"],
                missing_data=[],
                summary=f"Market regime unfavorable: trend={snap.trend_state}, liquidity={snap.liquidity_state}, risk={snap.risk_level}.",
            )

        if snap.trend_state == "uptrend" and snap.liquidity_state in _FAVORABLE_LIQUIDITY and snap.risk_level in _FAVORABLE_RISK:
            return self._opinion(
                context,
                stance="support",
                confidence=0.7,
                evidence=evidence,
                risks=[],
                missing_data=[],
                summary=f"Market regime favorable: trend={snap.trend_state}, liquidity={snap.liquidity_state}, risk={snap.risk_level}.",
            )

        return self._neutral(
            context,
            missing_data=[],
            evidence=evidence,
            summary=f"Mixed market regime: trend={snap.trend_state}, liquidity={snap.liquidity_state}, risk={snap.risk_level}.",
        )

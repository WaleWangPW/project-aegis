"""SectorAgent — Phase 3 §7.6. Reads the sector signal, MarketSnapshot's
sector_rotation, and Candidate.sector."""

from __future__ import annotations

from aegis.experts.base import BaseExpertAgent
from aegis.experts.context import AnalysisContext
from aegis.models.expert_opinion import ExpertOpinion


class SectorAgent(BaseExpertAgent):
    name = "SectorAgent"

    def analyze(self, context: AnalysisContext) -> ExpertOpinion:
        sector_sig = context.find_signal(signal_type="sector")

        if sector_sig is None or sector_sig.evidence_strength == "unknown":
            return self._neutral(
                context, missing_data=["sector_signal"],
                summary="No sector classification/rotation data available for this candidate.",
            )

        in_rotation = bool(isinstance(sector_sig.value, dict) and sector_sig.value.get("in_rotation"))
        evidence = [f"signal:{sector_sig.signal_id}"]
        snap = context.market_snapshot

        if in_rotation:
            return self._opinion(
                context, stance="support", confidence=0.6, evidence=evidence, risks=[], missing_data=[],
                summary="Candidate's sector is in the current market sector_rotation list.",
            )

        if snap is not None and snap.sentiment_state == "risk_off":
            return self._opinion(
                context, stance="oppose", confidence=0.5, evidence=evidence,
                risks=["sector_not_leading_in_risk_off_regime"], missing_data=[],
                summary="Candidate's sector is not in the current rotation list, and the market is risk_off.",
            )

        return self._neutral(
            context, missing_data=[], evidence=evidence,
            summary="Candidate's sector is not flagged as leading, but market regime is not clearly risk_off.",
        )

"""FundamentalAgent — Phase 3 §7.4. Presence-based only; no complex
fundamental model in P0.
"""

from __future__ import annotations

from aegis.experts.base import BaseExpertAgent
from aegis.experts.context import AnalysisContext
from aegis.models.expert_opinion import ExpertOpinion


class FundamentalAgent(BaseExpertAgent):
    name = "FundamentalAgent"

    def analyze(self, context: AnalysisContext) -> ExpertOpinion:
        fund_sig = context.find_signal(signal_type="fundamental")

        if fund_sig is None or fund_sig.evidence_strength == "unknown":
            return self._neutral(
                context, missing_data=["fundamental_signal"],
                summary="No usable fundamental data for this candidate.",
            )

        risk_flags = fund_sig.value.get("risk_flags") if isinstance(fund_sig.value, dict) else []
        evidence = [f"signal:{fund_sig.signal_id}"]

        if risk_flags:
            return self._opinion(
                context, stance="oppose", confidence=0.55, evidence=evidence, risks=list(risk_flags), missing_data=[],
                summary=f"Fundamental data flags risk(s): {', '.join(risk_flags)}.",
            )

        return self._opinion(
            context, stance="support", confidence=0.55, evidence=evidence, risks=[], missing_data=[],
            summary="Usable fundamental evidence present with no obvious valuation/fundamental risk flagged.",
        )

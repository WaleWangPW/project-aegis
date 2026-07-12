"""TrendAgent — Phase 3 §7.3. Reads the trend and relative-strength signals."""

from __future__ import annotations

from aegis.experts.base import BaseExpertAgent
from aegis.experts.context import AnalysisContext
from aegis.models.expert_opinion import ExpertOpinion


class TrendAgent(BaseExpertAgent):
    name = "TrendAgent"

    def analyze(self, context: AnalysisContext) -> ExpertOpinion:
        trend_sig = context.find_signal(signal_type="trend")
        rs_sig = context.find_signal(signal_type="relative_strength")

        missing = []
        if trend_sig is None or trend_sig.evidence_strength == "unknown":
            missing.append("trend_signal")
        if rs_sig is None or rs_sig.evidence_strength == "unknown":
            missing.append("relative_strength_signal")

        if trend_sig is None or trend_sig.evidence_strength == "unknown":
            return self._neutral(context, missing_data=missing, summary="Trend signal unavailable or unknown; insufficient price history.")

        direction = trend_sig.value.get("direction") if isinstance(trend_sig.value, dict) else None
        rs_weak = bool(
            rs_sig is not None
            and isinstance(rs_sig.value, dict)
            and rs_sig.value.get("relative_strength") is not None
            and rs_sig.value.get("relative_strength") < 0
        )

        evidence = [f"signal:{trend_sig.signal_id}"]
        if rs_sig is not None:
            evidence.append(f"signal:{rs_sig.signal_id}")

        if direction == "uptrend" and not rs_weak:
            return self._opinion(
                context, stance="support", confidence=0.65, evidence=evidence, risks=[], missing_data=missing,
                summary=f"Trend supports improvement ({direction}) and relative strength is not weak.",
            )

        if direction == "downtrend" or rs_weak:
            risks = []
            if direction == "downtrend":
                risks.append("trend_down")
            if rs_weak:
                risks.append("relative_weakness_vs_index")
            return self._opinion(
                context, stance="oppose", confidence=0.6, evidence=evidence, risks=risks, missing_data=missing,
                summary=f"Trend direction={direction}, relative strength weak={rs_weak}.",
            )

        return self._neutral(
            context, missing_data=missing, evidence=evidence,
            summary=f"Mixed trend signal (direction={direction}, rs_weak={rs_weak}).",
        )

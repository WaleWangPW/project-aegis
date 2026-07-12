"""TimingAgent — Phase 3 §7.7.

P0 simplification: "entry zone" / "overextension" is approximated from the
trend signal's recent_return magnitude (a large recent move is treated as
overextended/chasing risk) plus the volume signal's state. This is a proxy,
not a real entry-timing model — documented here so a later phase doesn't
mistake it for something more precise than it is.

Phase 3 only emits ExpertOpinion here. Phase 4's "Timing oppose => at most
Ready" decision rule is NOT implemented in this file.
"""

from __future__ import annotations

from aegis.experts.base import BaseExpertAgent
from aegis.experts.context import AnalysisContext
from aegis.models.expert_opinion import ExpertOpinion

OVEREXTENDED_RETURN_THRESHOLD = 0.15  # +/-15% over the trend signal's lookback


class TimingAgent(BaseExpertAgent):
    name = "TimingAgent"

    def analyze(self, context: AnalysisContext) -> ExpertOpinion:
        trend_sig = context.find_signal(signal_type="trend")
        vol_sig = context.find_signal(signal_type="volume")

        if trend_sig is None or trend_sig.evidence_strength == "unknown":
            missing = ["trend_signal"]
            if vol_sig is None or vol_sig.evidence_strength == "unknown":
                missing.append("volume_signal")
            return self._neutral(context, missing_data=missing, summary="Timing unclear: insufficient trend data.")

        direction = trend_sig.value.get("direction") if isinstance(trend_sig.value, dict) else None
        recent_return = trend_sig.value.get("recent_return") if isinstance(trend_sig.value, dict) else None
        overextended = recent_return is not None and abs(recent_return) > OVEREXTENDED_RETURN_THRESHOLD

        evidence = [f"signal:{trend_sig.signal_id}"]
        if vol_sig is not None:
            evidence.append(f"signal:{vol_sig.signal_id}")

        if direction == "uptrend" and not overextended:
            return self._opinion(
                context, stance="support", confidence=0.55, evidence=evidence, risks=[], missing_data=[],
                summary="Setup is trending up and not overextended (P0 proxy, no precise entry-zone model).",
            )

        if overextended or direction == "downtrend":
            risks = []
            if overextended:
                risks.append("overextended_recent_move")
            if direction == "downtrend":
                risks.append("poor_entry_location_downtrend")
            return self._opinion(
                context, stance="oppose", confidence=0.5, evidence=evidence, risks=risks, missing_data=[],
                summary=f"Timing unfavorable: direction={direction}, overextended={overextended}.",
            )

        return self._neutral(
            context, missing_data=[], evidence=evidence,
            summary=f"Timing unclear: direction={direction}, overextended={overextended}.",
        )

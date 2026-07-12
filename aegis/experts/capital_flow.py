"""CapitalFlowAgent — Phase 3 §7.5. Reads the volume signal as a
liquidity/turnover proxy (no real money-flow data source in P0)."""

from __future__ import annotations

from aegis.experts.base import BaseExpertAgent
from aegis.experts.context import AnalysisContext
from aegis.models.expert_opinion import ExpertOpinion


class CapitalFlowAgent(BaseExpertAgent):
    name = "CapitalFlowAgent"

    def analyze(self, context: AnalysisContext) -> ExpertOpinion:
        vol_sig = context.find_signal(signal_type="volume")

        if vol_sig is None or vol_sig.evidence_strength == "unknown":
            return self._neutral(
                context, missing_data=["volume_signal"],
                summary="No usable volume/capital-flow data for this candidate.",
            )

        state = vol_sig.value.get("state") if isinstance(vol_sig.value, dict) else None
        evidence = [f"signal:{vol_sig.signal_id}"]

        if state == "expansion":
            return self._opinion(
                context, stance="support", confidence=0.6, evidence=evidence, risks=[], missing_data=[],
                summary="Volume expansion with valid data — supportive price/volume confirmation.",
            )

        if state == "contraction":
            return self._opinion(
                context, stance="oppose", confidence=0.5, evidence=evidence, risks=["volume_contraction"], missing_data=[],
                summary="Volume contraction relative to its own average — weak capital-flow pattern.",
            )

        return self._neutral(
            context, missing_data=[], evidence=evidence,
            summary=f"Volume state is '{state}' — neither clear expansion nor contraction.",
        )

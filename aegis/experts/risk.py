"""RiskAgent — Phase 3 §7.8.

May output `veto` in Phase 3. It must NOT perform the Action-blocking
decision itself — Phase 4's Decision Engine consumes the veto, this agent
only records it as an opinion.
"""

from __future__ import annotations

from aegis.experts.base import BaseExpertAgent
from aegis.experts.context import AnalysisContext
from aegis.models.expert_opinion import ExpertOpinion

_VETO_FLAGS = {"invalid_bars", "suspended"}


class RiskAgent(BaseExpertAgent):
    name = "RiskAgent"

    def analyze(self, context: AnalysisContext) -> ExpertOpinion:
        risk_sig = context.find_signal(signal_type="risk")
        candidate = context.candidate

        critical_flags: list[str] = []
        if candidate is not None:
            if not candidate.liquidity_ok:
                critical_flags.append("liquidity_not_ok")
            if candidate.data_quality.status == "missing":
                critical_flags.append("data_quality_missing")

        if risk_sig is None or risk_sig.evidence_strength == "unknown":
            if critical_flags:
                return self._opinion(
                    context, stance="veto", confidence=0.7, evidence=[], risks=critical_flags,
                    missing_data=["risk_signal"],
                    summary=f"Risk signal unavailable and critical candidate-level flags present: {', '.join(critical_flags)}.",
                )
            return self._neutral(
                context, missing_data=["risk_signal"],
                summary="Risk unknown but no critical candidate-level flags detected.",
            )

        signal_flags = list(risk_sig.value.get("flags", [])) if isinstance(risk_sig.value, dict) else []
        all_flags = signal_flags + critical_flags
        evidence = [f"signal:{risk_sig.signal_id}"]

        veto_triggered = (
            bool(_VETO_FLAGS & set(all_flags))
            or "liquidity_not_ok" in all_flags
            or "data_quality_missing" in all_flags
            or ("high_volatility" in all_flags and "severe_drawdown" in all_flags)
        )
        if veto_triggered:
            return self._opinion(
                context, stance="veto", confidence=0.75, evidence=evidence, risks=all_flags, missing_data=[],
                summary=f"Unacceptable risk detected: {', '.join(all_flags)}.",
            )

        if "high_volatility" in all_flags or "severe_drawdown" in all_flags or "liquidity_risk" in all_flags:
            return self._opinion(
                context, stance="oppose", confidence=0.55, evidence=evidence, risks=all_flags, missing_data=[],
                summary=f"Elevated but not fatal risk: {', '.join(all_flags)}.",
            )

        if not all_flags:
            return self._opinion(
                context, stance="support", confidence=0.6, evidence=evidence, risks=[], missing_data=[],
                summary="Risk acceptable: no elevated volatility/drawdown/liquidity flags.",
            )

        return self._neutral(
            context, missing_data=[], evidence=evidence,
            summary=f"Risk flags present but not critical: {', '.join(all_flags)}.",
        )

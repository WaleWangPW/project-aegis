"""BaseExpertAgent — Phase 3 §6.1/§7.1.

Every agent returns exactly one `ExpertOpinion`: a plain vote
(support/oppose/neutral/veto), never a numeric score, never a
Watch/Ready/Action/Exit status. Agents must never raise on missing data —
missing data becomes `missing_data` entries on the opinion, never a guess.
`safe_analyze` is what `ExpertCommittee` actually calls: if `analyze()`
raises unexpectedly anyway, it is converted to a neutral opinion rather than
crashing the whole committee run (§6.3).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from aegis.experts.context import AnalysisContext
from aegis.models.expert_opinion import ExpertOpinion

_SHORT_NAMES = {
    "MarketRegimeAgent": "market_regime",
    "TrendAgent": "trend",
    "FundamentalAgent": "fundamental",
    "CapitalFlowAgent": "capital_flow",
    "SectorAgent": "sector",
    "TimingAgent": "timing",
    "RiskAgent": "risk",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class BaseExpertAgent:
    name: str = "BaseExpertAgent"

    def analyze(self, context: AnalysisContext) -> ExpertOpinion:
        raise NotImplementedError

    def safe_analyze(self, context: AnalysisContext) -> ExpertOpinion:
        """What ExpertCommittee actually calls. Never raises."""
        try:
            return self.analyze(context)
        except Exception as exc:  # noqa: BLE001 - deliberate, converted to a controlled opinion
            return self._opinion(
                context,
                stance="neutral",
                confidence=0.0,
                evidence=[],
                risks=[f"agent_error: {exc!r}"],
                missing_data=["agent_execution_failed"],
                summary=(
                    f"{self.name} raised an unexpected error and was degraded to a "
                    f"neutral opinion rather than crashing the committee run: {exc}"
                ),
            )

    def _opinion_id(self, context: AnalysisContext) -> str:
        short = _SHORT_NAMES.get(self.name, self.name.lower())
        return f"opn_{context.date.replace('-', '')}_{context.candidate.market}_{context.candidate.symbol}_{short}"

    def _opinion(
        self,
        context: AnalysisContext,
        *,
        stance: str,
        confidence: float,
        evidence: list[str],
        risks: list[str],
        missing_data: list[str],
        summary: str,
    ) -> ExpertOpinion:
        return ExpertOpinion(
            opinion_id=self._opinion_id(context),
            recommendation_id=context.provisional_recommendation_id,
            expert_name=self.name,
            stance=stance,
            confidence=confidence,
            evidence=evidence,
            risks=risks,
            missing_data=missing_data,
            summary=summary,
            created_at=_now_iso(),
        )

    def _neutral(
        self,
        context: AnalysisContext,
        *,
        missing_data: list[str],
        summary: str,
        evidence: Optional[list[str]] = None,
        risks: Optional[list[str]] = None,
        confidence: float = 0.4,
    ) -> ExpertOpinion:
        return self._opinion(
            context,
            stance="neutral",
            confidence=confidence,
            evidence=evidence or [],
            risks=risks or [],
            missing_data=missing_data,
            summary=summary,
        )

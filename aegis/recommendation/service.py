"""RecommendationService — Phase 4 §8.

Maps a DecisionRecord + candidate/market/opinion context into the canonical
RecommendationRecord (Master Spec ADR-001). Every support/oppose reason
traces back to a concrete `opinion_id` — nothing here is a fabricated
summary of "why", it is a formatted pointer to the real ExpertOpinion.
"""

from __future__ import annotations

from typing import Optional

from aegis.models.candidate import Candidate
from aegis.models.decision import DecisionRecord
from aegis.models.expert_opinion import ExpertOpinion
from aegis.models.holding import Holding
from aegis.models.market_snapshot import MarketSnapshot
from aegis.models.recommendation import RecommendationRecord


class RecommendationService:
    def create_from_decision(
        self,
        *,
        decision: DecisionRecord,
        candidate: Candidate,
        market_snapshot: MarketSnapshot,
        opinions: list[ExpertOpinion],
        holding: Optional[Holding] = None,
    ) -> RecommendationRecord:
        support_reasons = [
            f"{o.expert_name} support: {o.summary} (source_opinion_id={o.opinion_id})"
            for o in opinions
            if o.stance == "support"
        ]
        oppose_reasons = [
            f"{o.expert_name} {o.stance}: {o.summary} (source_opinion_id={o.opinion_id})"
            for o in opinions
            if o.stance in ("oppose", "veto")
        ]

        risks: list[str] = []
        for o in opinions:
            risks.extend(o.risks)

        missing_data: set[str] = set()
        for o in opinions:
            missing_data.update(o.missing_data)
        if missing_data:
            oppose_reasons.append(
                f"Missing data across experts: {', '.join(sorted(missing_data))} "
                f"(traced from {', '.join(o.opinion_id for o in opinions if o.missing_data)})."
            )

        record = RecommendationRecord(
            recommendation_id=decision.recommendation_id,
            date=market_snapshot.date,
            session=market_snapshot.session,
            symbol=candidate.symbol,
            name=candidate.name,
            market=candidate.market,
            sector=candidate.sector,
            status=decision.final_status,
            action_label=decision.final_action,
            market_snapshot_id=market_snapshot.snapshot_id,
            candidate_id=candidate.candidate_id,
            expert_opinions=[o.opinion_id for o in opinions],
            support_reasons=support_reasons,
            oppose_reasons=oppose_reasons,
            risks=sorted(set(risks)),
            invalidation_conditions=list(decision.invalidation_conditions),
            confidence=decision.confidence,
            decision_summary=decision.decision_reason,
            paper_trade_id=None,
            review_id=None,
            lifecycle_status="open",
            created_at=decision.created_at,
            updated_at=decision.created_at,
        )
        self.validate(record)
        return record

    def validate(self, record: RecommendationRecord) -> None:
        """Defensive re-check on top of pydantic's own validators — useful
        for records assembled by another path and handed to this service
        directly, and makes the PHASE4 doc §8 validation list independently
        testable.
        """
        if not record.recommendation_id:
            raise ValueError("RecommendationRecord.recommendation_id must be set.")
        if not record.market_snapshot_id:
            raise ValueError("RecommendationRecord.market_snapshot_id must be set.")
        if not record.candidate_id:
            raise ValueError("RecommendationRecord.candidate_id must be set.")
        if not record.decision_summary:
            raise ValueError("RecommendationRecord.decision_summary must be non-empty.")
        if record.support_reasons is None or record.oppose_reasons is None:
            raise ValueError("support_reasons/oppose_reasons must be arrays, never null.")
        if record.risks is None:
            raise ValueError("risks must be an array, never null.")
        if record.status == "Action" and not record.invalidation_conditions:
            raise ValueError("Action status requires non-empty invalidation_conditions.")

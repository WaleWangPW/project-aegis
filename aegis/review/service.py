"""ReviewService — Phase 6 §5.4.

Reads existing `RecommendationRecord`/`DecisionRecord`/`ExpertOpinion`/
`PaperTrade` records (never re-computes a decision) and produces a
`ReviewRecord` that evaluates *decision quality*, not just realized return
(Master Spec §8.9). Deliberately deterministic — no LLM judging, no
composite scoring (ADR-002 applies here too: decision_quality is a rule-
based classification, never a weighted score).

`ReviewRecord.outcome`/`decision_quality` do not have literal "inconclusive"/
"unknown" values in the Phase 0 model (`Outcome`/`DecisionQuality` in
`aegis/models/review.py`) — per PHASE6 doc §5.4 rule 6 ("...or equivalent
existing enum value"), this module maps "not enough data yet" to the
closest existing values: `outcome="pending"`, `decision_quality="unclear"`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from aegis.models.decision import DecisionRecord
from aegis.models.investment_memory import InvestmentMemory
from aegis.models.paper_trade import PaperTrade
from aegis.models.recommendation import RecommendationRecord
from aegis.models.review import DecisionQuality, Horizon, Outcome, ReviewRecord
from aegis.paper.metrics import compute_return
from aegis.paper.repository import PaperTradeRepository
from aegis.recommendation.repository import RecommendationRepository
from aegis.review import metrics as review_metrics
from aegis.review.repository import ReviewRepository
from aegis.utils.jsonl import read_jsonl

_HORIZON_FIELDS: dict[str, str] = {"5d": "return_5d", "10d": "return_10d", "20d": "return_20d", "40d": "return_40d"}
_TRADE_HORIZONS: tuple[str, ...] = ("5d", "10d", "20d", "40d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class ReviewService:
    def __init__(
        self,
        review_repository: ReviewRepository,
        paper_repository: PaperTradeRepository,
        recommendation_repository: RecommendationRepository,
        records_dir: Optional[str | Path] = None,
    ):
        self.review_repository = review_repository
        self.paper_repository = paper_repository
        self.recommendation_repository = recommendation_repository
        # ExpertOpinion has no dedicated repository class yet (Phase 3/4
        # both just read/write `expert_opinions.jsonl` directly via the
        # shared jsonl utils) — kept consistent with that existing pattern
        # rather than inventing a new repository class this phase doesn't
        # otherwise need.
        self.records_dir = Path(records_dir) if records_dir is not None else self.paper_repository.records_dir

    # -- public API (PHASE6 doc §5.4) -----------------------------------

    def generate_due_reviews(self, date: str) -> list[ReviewRecord]:
        """Generate every ReviewRecord that has newly become due as of
        `date` — one per (recommendation_id, horizon) that has real
        PaperTrade data and no existing review yet."""
        generated: list[ReviewRecord] = []
        recommendations_by_id = {r.recommendation_id: r for r in self.recommendation_repository.list_recommendations()}

        for trade in self.paper_repository.list_all():
            rec = recommendations_by_id.get(trade.recommendation_id)
            if rec is None:
                continue  # no recommendation on file to review against — skip, don't fabricate one

            for horizon in _TRADE_HORIZONS:
                if getattr(trade, _HORIZON_FIELDS[horizon]) is None:
                    continue  # not due yet
                if self.review_repository.exists_for(rec.recommendation_id, horizon):
                    continue
                review = self.review_recommendation(rec, horizon)
                self.review_repository.append(review)
                generated.append(review)

            if trade.status == "closed" and not self.review_repository.exists_for(rec.recommendation_id, "exit"):
                review = self.review_recommendation(rec, "exit")
                self.review_repository.append(review)
                generated.append(review)

        return generated

    def review_recommendation(self, rec: RecommendationRecord, horizon: str) -> ReviewRecord:
        trade = self._find_trade(rec.recommendation_id)
        decision = self._find_decision(rec.recommendation_id)
        actual_return, max_drawdown = self._resolve_return_and_drawdown(trade, horizon)
        outcome = self._classify_outcome(actual_return)
        decision_quality = self._classify_decision_quality(rec, decision, actual_return)
        expert_contribution = self._build_expert_contribution(rec)
        lessons = self._build_lessons(rec, decision, actual_return, decision_quality)

        review_date = trade.updated_at[:10] if trade is not None else rec.date

        return ReviewRecord(
            review_id=f"rev_{rec.date.replace('-', '')}_{rec.market}_{rec.symbol}_{horizon}",
            recommendation_id=rec.recommendation_id,
            paper_trade_id=trade.paper_trade_id if trade is not None else None,
            review_date=review_date,
            horizon=horizon,  # type: ignore[arg-type]
            outcome=outcome,
            actual_return=actual_return,
            max_drawdown=max_drawdown,
            decision_quality=decision_quality,
            success_reason=self._success_reason(rec, outcome),
            failure_reason=self._failure_reason(rec, decision, outcome),
            expert_contribution=expert_contribution,
            lessons=lessons,
            created_at=_now_iso(),
        )

    def compute_metrics(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        reviews = self.review_repository.list_all()
        if start_date is not None:
            reviews = [r for r in reviews if r.review_date >= start_date]
        if end_date is not None:
            reviews = [r for r in reviews if r.review_date <= end_date]

        market_by_rec, sector_by_rec = self._market_sector_lookup()

        return {
            "review_count": len(reviews),
            "action_success_rate": review_metrics.compute_action_success_rate(reviews),
            "average_return": review_metrics.compute_average_return(reviews),
            "max_drawdown": review_metrics.compute_max_drawdown_summary(reviews),
            "win_loss_count": review_metrics.compute_win_loss_count(reviews),
            "market_breakdown": review_metrics.compute_breakdown_by_key(reviews, market_by_rec),
            "sector_breakdown": review_metrics.compute_breakdown_by_key(reviews, sector_by_rec),
        }

    def export_lessons(self, reviews: list[ReviewRecord]) -> list[InvestmentMemory]:
        """Thin pass-through used by `MemoryService` (Phase 6 §5.6) — kept
        here (rather than only in MemoryService) since the doc lists it as
        a `ReviewService` method. Actual `InvestmentMemory` construction is
        `MemoryService.create_from_review`'s job; this just flattens."""
        memories: list[InvestmentMemory] = []
        from aegis.memory.service import MemoryService  # local import: avoids a service<->service import cycle

        memory_service = MemoryService()
        for review in reviews:
            memories.extend(memory_service.create_from_review(review))
        return memories

    # -- internals -------------------------------------------------------

    def _find_trade(self, recommendation_id: str) -> Optional[PaperTrade]:
        matches = self.paper_repository.find_by_recommendation_id(recommendation_id)
        return matches[0] if matches else None

    def _find_decision(self, recommendation_id: str) -> Optional[DecisionRecord]:
        for decision in self.recommendation_repository.list_decisions():
            if decision.recommendation_id == recommendation_id:
                return decision
        return None

    def _resolve_return_and_drawdown(
        self, trade: Optional[PaperTrade], horizon: str
    ) -> tuple[Optional[float], Optional[float]]:
        if trade is None:
            return None, None
        if horizon == "exit":
            if trade.exit_price is not None:
                return compute_return(trade.entry_price, trade.exit_price), trade.max_drawdown
            return None, trade.max_drawdown
        field = _HORIZON_FIELDS.get(horizon)
        if field is None:
            return None, trade.max_drawdown
        return getattr(trade, field), trade.max_drawdown

    def _classify_outcome(self, actual_return: Optional[float]) -> Outcome:
        if actual_return is None:
            return "pending"  # stands in for "inconclusive" (doc §5.4 rule 6)
        if actual_return > 0:
            return "success"
        if actual_return < 0:
            return "failure"
        return "mixed"

    def _classify_decision_quality(
        self,
        rec: RecommendationRecord,
        decision: Optional[DecisionRecord],
        actual_return: Optional[float],
    ) -> DecisionQuality:
        """Deliberately NOT a direct function of return sign (PHASE6 doc
        §7.2 test 4) — a well-reasoned Action that loses money can still be
        a "reasonable_decision", and a thin/veto'd one that happens to gain
        is not automatically "good_decision"."""
        if actual_return is None:
            return "unclear"  # stands in for "unknown" (doc §5.4 rule 6)

        veto_triggered = bool(decision and decision.risk_veto_triggered)
        has_solid_process = bool(rec.invalidation_conditions) and bool(rec.support_reasons) and not veto_triggered

        if actual_return > 0:
            return "good_decision" if has_solid_process else "reasonable_decision"
        if actual_return < 0:
            return "reasonable_decision" if has_solid_process else "poor_decision"
        return "reasonable_decision"

    def _success_reason(self, rec: RecommendationRecord, outcome: Outcome) -> Optional[str]:
        if outcome != "success":
            return None
        return rec.decision_summary or "支持理由兑现，Action 判断成立。"

    def _failure_reason(
        self, rec: RecommendationRecord, decision: Optional[DecisionRecord], outcome: Outcome
    ) -> Optional[str]:
        if outcome != "failure":
            return None
        if decision and decision.risk_veto_triggered:
            return "RiskAgent 曾一票否决，本次结果验证了该风险判断。"
        return rec.decision_summary or "实际结果未达支持理由预期，需结合复盘归档。"

    def _build_expert_contribution(self, rec: RecommendationRecord) -> dict[str, str]:
        opinion_ids = set(rec.expert_opinions)
        if not opinion_ids:
            return {"status": "DATA_GAP: RecommendationRecord 未记录 expert_opinions 引用"}

        opinions_path = self.records_dir / "expert_opinions.jsonl"
        contribution: dict[str, str] = {}
        for row in read_jsonl(opinions_path):
            if row.get("opinion_id") in opinion_ids:
                contribution[row.get("expert_name", "unknown")] = row.get("stance", "unknown")

        if not contribution:
            return {"status": "DATA_GAP: 未找到对应的 ExpertOpinion 记录"}
        return contribution

    def _build_lessons(
        self,
        rec: RecommendationRecord,
        decision: Optional[DecisionRecord],
        actual_return: Optional[float],
        decision_quality: DecisionQuality,
    ) -> list[str]:
        if actual_return is None:
            return []  # nothing conclusive to learn from yet

        lessons: list[str] = []
        if decision_quality == "good_decision":
            lessons.append(f"{rec.symbol}（{rec.market}）：证据充分且结果兑现，支持理由/失效条件设计可复用。")
        elif decision_quality == "reasonable_decision" and actual_return < 0:
            lessons.append(f"{rec.symbol}（{rec.market}）：流程扎实但结果未达预期，说明证据充分不保证收益，需持续观察该类信号的实际命中率。")
        elif decision_quality == "poor_decision":
            lessons.append(f"{rec.symbol}（{rec.market}）：支持依据薄弱且结果不佳，后续同类候选应提高证据门槛。")

        if decision and decision.risk_veto_triggered and actual_return < 0:
            lessons.append("RiskAgent 一票否决在本次事后验证是正确的风险判断。")

        return lessons

    def _market_sector_lookup(self) -> tuple[dict[str, str], dict[str, str]]:
        market_by_rec: dict[str, str] = {}
        sector_by_rec: dict[str, str] = {}
        for rec in self.recommendation_repository.list_recommendations():
            market_by_rec[rec.recommendation_id] = rec.market
            sector_by_rec[rec.recommendation_id] = rec.sector or "未知行业"
        return market_by_rec, sector_by_rec

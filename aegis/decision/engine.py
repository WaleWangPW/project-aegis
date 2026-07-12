"""DecisionEngine — Phase 4 §5-6.

Converts one candidate's ExpertOpinion evidence into a DecisionRecord +
RecommendationRecord via evidence voting — never a weighted composite
score (ADR-002). Implements the 8 hard rules from PHASE4 doc §5.4 exactly:

1. Risk veto blocks Action.
2. Timing oppose caps status at Ready.
3. Market high risk downgrades one level (unless Exit is triggered).
4. Missing critical data blocks Action.
5. Support reasons trace to ExpertOpinion (via RecommendationService).
6. Oppose/veto/missing-data reasons are preserved (via RecommendationService).
7. Action requires invalidation conditions.
8. No composite score — confidence is decision-reliability metadata only.

Note on scope: "invalidation condition is triggered" (PHASE4 doc §6.4) would
require re-checking a *previously issued* RecommendationRecord's own
invalidation conditions against fresh data — that history lookup is not
part of this phase's inputs (DecisionEngine only sees the current
MarketSnapshot/Candidate/ExpertOpinion/Holding), so it is not implemented
here. The other three Exit triggers (RiskAgent veto on a holding, clear
trend breakdown, extreme market risk + high holding risk) are implemented.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from aegis.decision.confidence import compute_decision_confidence
from aegis.models.candidate import Candidate
from aegis.models.decision import DecisionRecord
from aegis.models.expert_opinion import ExpertOpinion
from aegis.models.holding import Holding
from aegis.models.market_snapshot import MarketSnapshot
from aegis.models.recommendation import RecommendationRecord
from aegis.recommendation.service import RecommendationService

_STATUS_ORDER = ["Watch", "Ready", "Action"]  # Exit is handled separately, never part of this ladder


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _find_opinion(opinions: list[ExpertOpinion], expert_name: str) -> Optional[ExpertOpinion]:
    return next((o for o in opinions if o.expert_name == expert_name), None)


def _has_critical_data(
    *,
    candidate: Candidate,
    market_snapshot: Optional[MarketSnapshot],
    holding: Optional[Holding],
    expert_opinions: list[ExpertOpinion],
) -> bool:
    """Critical missing data per PHASE4 doc §5.4 rule 4: current/entry
    price, recent OHLCV, liquidity, risk metrics. Candidate/Signal models
    don't carry a raw price field directly, so this is a deliberate proxy:
    a missing `trend_signal`/`risk_signal` on any opinion means the
    underlying bars (OHLCV) were unavailable when Phase 3 computed signals.
    """
    all_missing: set[str] = set()
    for opinion in expert_opinions:
        all_missing.update(opinion.missing_data)

    if "trend_signal" in all_missing or "risk_signal" in all_missing:
        return False
    if not candidate.liquidity_ok:
        return False
    if candidate.data_quality.status in ("missing", "unavailable"):
        return False
    if market_snapshot is None or market_snapshot.risk_level == "unknown":
        return False
    if holding is not None and holding.current_price is None:
        return False
    return True


def _build_invalidation_conditions(
    *,
    candidate: Candidate,
    market_snapshot: Optional[MarketSnapshot],
    expert_opinions: list[ExpertOpinion],
) -> list[str]:
    """Deterministic, rule-based invalidation conditions traced to a
    concrete opinion/snapshot reference — never a generic placeholder
    string with no evidence behind it.
    """
    conditions: list[str] = []

    trend_opinion = _find_opinion(expert_opinions, "TrendAgent")
    if trend_opinion is not None and trend_opinion.stance != "neutral":
        conditions.append(
            f"TrendAgent stance reverses from '{trend_opinion.stance}' (source_opinion_id={trend_opinion.opinion_id})."
        )

    risk_opinion = _find_opinion(expert_opinions, "RiskAgent")
    if risk_opinion is not None and risk_opinion.stance != "veto":
        conditions.append(
            f"RiskAgent stance moves to veto (source_opinion_id={risk_opinion.opinion_id})."
        )

    if market_snapshot is not None and market_snapshot.trend_state != "unknown":
        conditions.append(
            f"Market regime for {candidate.market} deteriorates to downtrend/high risk "
            f"(market_snapshot_id={market_snapshot.snapshot_id})."
        )

    return conditions


def _raw_status(
    *,
    support_count: int,
    oppose_count: int,
    timing_oppose: bool,
    has_critical: bool,
    has_invalidation: bool,
    confidence: float,
    action_min_support: int,
    action_min_confidence: float,
    ready_min_support: int,
    ready_min_confidence: float,
) -> str:
    can_action = (
        not timing_oppose
        and support_count >= action_min_support
        and has_critical
        and has_invalidation
        and confidence >= action_min_confidence
        and oppose_count < support_count  # oppose reasons present but not fatal
    )
    if can_action:
        return "Action"

    # Ready rule 6.2: "TimingAgent opposes but evidence is otherwise strong"
    # -> still Ready-eligible if support is at Action-grade strength.
    timing_ok_for_ready = (not timing_oppose) or support_count >= action_min_support
    can_ready = (
        support_count >= ready_min_support
        and timing_ok_for_ready
        and has_invalidation
        and confidence >= ready_min_confidence
    )
    if can_ready:
        return "Ready"

    return "Watch"


def _apply_market_downgrade(status: str, market_high_risk: bool) -> str:
    if not market_high_risk or status not in _STATUS_ORDER:
        return status
    idx = _STATUS_ORDER.index(status)
    return _STATUS_ORDER[max(0, idx - 1)]


def _check_exit(
    *,
    holding: Optional[Holding],
    risk_veto_triggered: bool,
    trend_opinion: Optional[ExpertOpinion],
    market_snapshot: Optional[MarketSnapshot],
    risk_opinion: Optional[ExpertOpinion],
) -> bool:
    if holding is None:
        return False
    if risk_veto_triggered:
        return True  # "RiskAgent vetoes a current holding"
    if trend_opinion is not None and trend_opinion.stance == "oppose":
        return True  # "trend breakdown is clear" (proxy: TrendAgent opposes)
    if (
        market_snapshot is not None
        and market_snapshot.risk_level == "high"
        and risk_opinion is not None
        and risk_opinion.stance in ("oppose", "veto")
    ):
        return True  # "market risk is extreme and holding risk is high"
    return False


def _final_action_label(status: str, holding: Optional[Holding]) -> str:
    """Descriptive metadata only — never a real or virtual trade instruction."""
    if status == "Exit":
        return "exit_position" if holding is not None else "avoid"
    if status == "Action":
        return "add_to_position" if holding is not None else "consider_entry"
    if status == "Ready":
        return "monitor_for_add" if holding is not None else "prepare_entry_plan"
    return "hold_and_monitor" if holding is not None else "monitor"


def _why_not_action(
    *,
    final_status: str,
    risk_veto_triggered: bool,
    timing_oppose: bool,
    support_count: int,
    action_min_support: int,
    has_critical: bool,
    has_invalidation: bool,
    confidence: float,
    action_min_confidence: float,
    market_high_risk: bool,
) -> Optional[str]:
    if final_status == "Action":
        return None
    if risk_veto_triggered:
        return "risk_veto_triggered"
    if timing_oppose:
        return "timing_agent_opposes"
    if not has_critical:
        return "missing_critical_data"
    if not has_invalidation:
        return "no_invalidation_conditions"
    if support_count < action_min_support:
        return f"insufficient_support ({support_count} < {action_min_support})"
    if confidence < action_min_confidence:
        return f"confidence_below_threshold ({confidence:.2f} < {action_min_confidence})"
    if market_high_risk:
        return "market_high_risk_downgrade"
    return "evidence_not_action_grade"


class DecisionEngine:
    def __init__(self, recommendation_service: Optional[RecommendationService] = None):
        self.recommendation_service = recommendation_service or RecommendationService()

    def decide(
        self,
        *,
        market_snapshot: MarketSnapshot,
        candidate: Candidate,
        expert_opinions: list[ExpertOpinion],
        holding: Optional[Holding] = None,
        config: Optional[dict] = None,
    ) -> tuple[DecisionRecord, RecommendationRecord]:
        config = config or {}
        decision_cfg = config.get("decision", {})
        action_cfg = decision_cfg.get("action", {})
        ready_cfg = decision_cfg.get("ready", {})
        downgrade_cfg = decision_cfg.get("downgrade", {})

        risk_opinion = _find_opinion(expert_opinions, "RiskAgent")
        timing_opinion = _find_opinion(expert_opinions, "TimingAgent")
        trend_opinion = _find_opinion(expert_opinions, "TrendAgent")
        market_regime_opinion = _find_opinion(expert_opinions, "MarketRegimeAgent")

        risk_veto_triggered = risk_opinion is not None and risk_opinion.stance == "veto"
        timing_oppose = timing_opinion is not None and timing_opinion.stance == "oppose"
        market_high_risk = (market_snapshot is not None and market_snapshot.risk_level == "high") or (
            market_regime_opinion is not None and market_regime_opinion.stance == "oppose"
        )

        support_count = sum(1 for o in expert_opinions if o.stance == "support")
        oppose_count = sum(1 for o in expert_opinions if o.stance == "oppose")
        neutral_count = sum(1 for o in expert_opinions if o.stance == "neutral")
        veto_count = sum(1 for o in expert_opinions if o.stance == "veto")

        has_critical = _has_critical_data(
            candidate=candidate, market_snapshot=market_snapshot, holding=holding, expert_opinions=expert_opinions
        )
        confidence = compute_decision_confidence(
            expert_opinions=expert_opinions,
            market_snapshot=market_snapshot,
            candidate=candidate,
            has_critical_data=has_critical,
        )

        invalidation_conditions = _build_invalidation_conditions(
            candidate=candidate, market_snapshot=market_snapshot, expert_opinions=expert_opinions
        )
        has_invalidation = bool(invalidation_conditions)
        if not has_invalidation:
            confidence = min(confidence, 0.55)  # rule 7 / §7 hard cap

        action_min_support = action_cfg.get("min_support_count", 3)
        action_min_confidence = action_cfg.get("min_confidence", 0.65)
        ready_min_support = ready_cfg.get("min_support_count", 2)
        ready_min_confidence = ready_cfg.get("min_confidence", 0.45)

        if risk_veto_triggered:
            # Rule 1: veto always blocks Action outright, regardless of any
            # other evidence. Config may name the ceiling, but it may never
            # resolve to "Action" — that would violate the acceptance rule.
            raw_status = downgrade_cfg.get("risk_veto_max_status", "Watch")
            if raw_status == "Action":
                raw_status = "Watch"
        else:
            raw_status = _raw_status(
                support_count=support_count,
                oppose_count=oppose_count,
                timing_oppose=timing_oppose,
                has_critical=has_critical,
                has_invalidation=has_invalidation,
                confidence=confidence,
                action_min_support=action_min_support,
                action_min_confidence=action_min_confidence,
                ready_min_support=ready_min_support,
                ready_min_confidence=ready_min_confidence,
            )

        exit_triggered = _check_exit(
            holding=holding,
            risk_veto_triggered=risk_veto_triggered,
            trend_opinion=trend_opinion,
            market_snapshot=market_snapshot,
            risk_opinion=risk_opinion,
        )
        if exit_triggered:
            final_status = "Exit"
        else:
            # Rule: no holding/open position -> never assign Exit just
            # because a new candidate is bad; use Watch instead (already
            # the floor of _raw_status/_apply_market_downgrade).
            final_status = _apply_market_downgrade(raw_status, market_high_risk)

        final_action = _final_action_label(final_status, holding)
        why_not_action = _why_not_action(
            final_status=final_status,
            risk_veto_triggered=risk_veto_triggered,
            timing_oppose=timing_oppose,
            support_count=support_count,
            action_min_support=action_min_support,
            has_critical=has_critical,
            has_invalidation=has_invalidation,
            confidence=confidence,
            action_min_confidence=action_min_confidence,
            market_high_risk=market_high_risk,
        )

        created_at = _now_iso()
        id_suffix = f"{market_snapshot.date.replace('-', '')}_{market_snapshot.session}_{candidate.market}_{candidate.symbol}"
        decision_reason = (
            f"support={support_count}, oppose={oppose_count}, neutral={neutral_count}, veto={veto_count}, "
            f"risk_veto={risk_veto_triggered}, timing_oppose={timing_oppose}, market_high_risk={market_high_risk}, "
            f"confidence={confidence:.2f} -> {final_status}."
        )

        decision_record = DecisionRecord(
            decision_id=f"dec_{id_suffix}",
            recommendation_id=f"rec_{id_suffix}",
            final_status=final_status,
            final_action=final_action,
            support_count=support_count,
            oppose_count=oppose_count,
            neutral_count=neutral_count,
            veto_count=veto_count,
            risk_veto_triggered=risk_veto_triggered,
            confidence=confidence,
            decision_reason=decision_reason,
            why_not_action=why_not_action,
            invalidation_conditions=invalidation_conditions,
            created_at=created_at,
        )

        recommendation_record = self.recommendation_service.create_from_decision(
            decision=decision_record,
            candidate=candidate,
            market_snapshot=market_snapshot,
            opinions=expert_opinions,
            holding=holding,
        )

        return decision_record, recommendation_record

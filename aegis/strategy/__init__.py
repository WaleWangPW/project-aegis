"""Historical strategy sandbox package."""

from aegis.strategy.library import StrategyCandidateLibrary, default_strategy_candidates
from aegis.strategy.research_bridge import build_research_bridge_report, build_strategy_update_proposals
from aegis.strategy.sandbox import build_strategy_sandbox_report, evaluate_strategy_candidate
from aegis.strategy.suggestion_gate import build_suggestion_drafts, build_suggestion_gate_report

__all__ = [
    "StrategyCandidateLibrary",
    "build_research_bridge_report",
    "build_suggestion_drafts",
    "build_suggestion_gate_report",
    "build_strategy_sandbox_report",
    "build_strategy_update_proposals",
    "default_strategy_candidates",
    "evaluate_strategy_candidate",
]

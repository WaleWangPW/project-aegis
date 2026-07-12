"""ExpertCommittee — Phase 3 §6.3.

Runs enabled agents in a fixed, deterministic order. One ExpertOpinion per
enabled agent per candidate. An agent that raises unexpectedly is degraded
to a neutral opinion (via `BaseExpertAgent.safe_analyze`) rather than
silently suppressed or allowed to crash the whole run.
"""

from __future__ import annotations

from typing import Optional

from aegis.experts.base import BaseExpertAgent
from aegis.experts.capital_flow import CapitalFlowAgent
from aegis.experts.context import AnalysisContext
from aegis.experts.fundamental import FundamentalAgent
from aegis.experts.market_regime import MarketRegimeAgent
from aegis.experts.risk import RiskAgent
from aegis.experts.sector import SectorAgent
from aegis.experts.timing import TimingAgent
from aegis.experts.trend import TrendAgent
from aegis.models.expert_opinion import ExpertOpinion

# Fixed, deterministic order — required by PHASE3 doc §6.3/§9.5.
DEFAULT_AGENT_CLASSES = [
    MarketRegimeAgent,
    TrendAgent,
    FundamentalAgent,
    CapitalFlowAgent,
    SectorAgent,
    TimingAgent,
    RiskAgent,
]


def _build_enabled_agents(config: Optional[dict]) -> list[BaseExpertAgent]:
    experts_cfg = (config or {}).get("experts", {}) or {}
    agents: list[BaseExpertAgent] = []
    for cls in DEFAULT_AGENT_CLASSES:
        entry = experts_cfg.get(cls.name)
        enabled = entry.get("enabled", True) if isinstance(entry, dict) else True
        if enabled:
            agents.append(cls())
    return agents


class ExpertCommittee:
    def __init__(self, agents: Optional[list[BaseExpertAgent]] = None, config: Optional[dict] = None):
        self.agents = agents if agents is not None else _build_enabled_agents(config)

    def analyze_candidate(self, context: AnalysisContext) -> list[ExpertOpinion]:
        return [agent.safe_analyze(context) for agent in self.agents]

    def analyze_candidates(self, contexts: list[AnalysisContext]) -> list[ExpertOpinion]:
        opinions: list[ExpertOpinion] = []
        for context in contexts:
            opinions.extend(self.analyze_candidate(context))
        return opinions

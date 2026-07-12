"""Expert Committee — Phase 3 §6.

`BaseExpertAgent` + `AnalysisContext` + `ExpertCommittee` + the 7 P0 agents.
Every agent returns exactly one `ExpertOpinion` (support/oppose/neutral/veto)
— never a Watch/Ready/Action/Exit status and never a weighted score. That
mapping is Phase 4 Decision Engine's job, not this package's.
"""

from .base import BaseExpertAgent
from .capital_flow import CapitalFlowAgent
from .committee import ExpertCommittee
from .context import AnalysisContext, provisional_recommendation_id
from .fundamental import FundamentalAgent
from .market_regime import MarketRegimeAgent
from .risk import RiskAgent
from .sector import SectorAgent
from .timing import TimingAgent
from .trend import TrendAgent

__all__ = [
    "BaseExpertAgent",
    "AnalysisContext",
    "provisional_recommendation_id",
    "ExpertCommittee",
    "MarketRegimeAgent",
    "TrendAgent",
    "FundamentalAgent",
    "CapitalFlowAgent",
    "SectorAgent",
    "TimingAgent",
    "RiskAgent",
]

"""AnalysisContext — Phase 3 §6.2.

Because Phase 4 has not yet created `RecommendationRecord`, this uses a
deterministic *provisional* ID for `ExpertOpinion.recommendation_id` — a
placeholder for linking opinions later, not a persisted recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from aegis.models.candidate import Candidate
from aegis.models.holding import Holding
from aegis.models.market_snapshot import MarketSnapshot
from aegis.models.portfolio_snapshot import PortfolioSnapshot
from aegis.models.signal import Signal


def provisional_recommendation_id(date: str, session: str, market: str, symbol: str) -> str:
    return f"rec_{date.replace('-', '')}_{session}_{market}_{symbol}"


@dataclass
class AnalysisContext:
    date: str
    session: str
    candidate: Candidate
    market_snapshot: Optional[MarketSnapshot] = None
    holding: Optional[Holding] = None
    signals: list[Signal] = field(default_factory=list)
    portfolio_snapshot: Optional[PortfolioSnapshot] = None
    data_gaps: list[dict] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    provisional_recommendation_id: str = ""

    def __post_init__(self) -> None:
        if not self.provisional_recommendation_id:
            self.provisional_recommendation_id = provisional_recommendation_id(
                self.date, self.session, self.candidate.market, self.candidate.symbol
            )

    def find_signal(self, *, signal_type: Optional[str] = None, signal_name: Optional[str] = None) -> Optional[Signal]:
        """First matching signal, or None. Agents use this instead of
        reaching into `self.signals` directly so the "missing signal"
        degrade-to-neutral path is uniform across agents.
        """
        for sig in self.signals:
            if signal_name is not None and sig.signal_name != signal_name:
                continue
            if signal_type is not None and sig.signal_type != signal_type:
                continue
            return sig
        return None

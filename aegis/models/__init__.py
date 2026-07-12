"""Typed data model skeletons for Project Aegis (Master Spec §7-8).

Phase 0 scope: models only, no business logic, no persistence, no
composite scoring. Every model mirrors the field tables in
Project_Aegis_MASTER_SPEC.md exactly so later phases (Universe Builder,
Expert Committee, Decision Engine, Paper Trading, Review, Backtest) have a
single, already-agreed shape to write into.
"""

from .common import Currency, DataQuality, Market, RecommendationStatus, Session, Stance
from .market_snapshot import MarketSnapshot
from .holding import Holding
from .candidate import Candidate
from .signal import Signal
from .expert_opinion import ExpertOpinion
from .recommendation import RecommendationRecord
from .decision import DecisionRecord
from .paper_trade import PaperTrade
from .review import ReviewRecord
from .portfolio_snapshot import PortfolioSnapshot
from .investment_memory import InvestmentMemory

__all__ = [
    "Currency",
    "DataQuality",
    "Market",
    "RecommendationStatus",
    "Session",
    "Stance",
    "MarketSnapshot",
    "Holding",
    "Candidate",
    "Signal",
    "ExpertOpinion",
    "RecommendationRecord",
    "DecisionRecord",
    "PaperTrade",
    "ReviewRecord",
    "PortfolioSnapshot",
    "InvestmentMemory",
]

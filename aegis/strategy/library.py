"""Strategy candidate library.

The library stores explicit, reviewable strategy candidates for repeatable
sandbox evaluation. It is not an optimizer and never changes strategy rules by
itself.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from aegis.models.strategy import StrategyCandidate, StrategyPassCriteria

SCHEMA_VERSION = "strategy_candidate_library.v1"


class StrategyLibraryError(ValueError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_strategy_candidates(*, created_at: Optional[str] = None) -> list[StrategyCandidate]:
    created = created_at or _now_iso()
    return [
        StrategyCandidate(
            strategy_id="value_quality_defensive_a",
            name="A-share value quality defensive",
            market="A",
            universe="A-share liquid large/mid cap with valuation and quality filters",
            factor_family="multi_factor",
            entry_rule="Prefer reasonable valuation, positive profitability, cash-flow quality, and no major risk veto.",
            exit_rule="Sandbox 20 trading-day review; real decisions remain manual and simulation-only.",
            exit_horizon_days=20,
            risk_controls=["liquidity_filter", "risk_veto", "max_drawdown_floor", "no_single_factor_action"],
            pass_criteria=StrategyPassCriteria(
                min_sample_count=4,
                min_win_rate=0.5,
                min_average_return=0.01,
                max_drawdown_floor=-0.08,
            ),
            source_research_refs=["S&P DJI China A-share factor research", "Aegis Evidence Rule"],
            created_at=created,
        ),
        StrategyCandidate(
            strategy_id="low_volatility_dividend_h",
            name="Hong Kong low volatility dividend",
            market="H",
            universe="Hong Kong liquid shares with dividend and volatility filters",
            factor_family="multi_factor",
            entry_rule="Prefer lower realized volatility, sustainable dividend, liquidity, and no event risk block.",
            exit_rule="Sandbox 20 trading-day review; no automatic execution.",
            exit_horizon_days=20,
            risk_controls=["liquidity_filter", "stock_connect_awareness", "event_risk_block", "max_drawdown_floor"],
            pass_criteria=StrategyPassCriteria(
                min_sample_count=4,
                min_win_rate=0.5,
                min_average_return=0.008,
                max_drawdown_floor=-0.09,
            ),
            source_research_refs=["S&P DJI Hong Kong smart beta research", "Aegis Risk Veto"],
            created_at=created,
        ),
        StrategyCandidate(
            strategy_id="risk_adjusted_momentum_us",
            name="U.S. risk-adjusted momentum",
            market="US",
            universe="U.S. large cap candidates with momentum plus quality and drawdown controls",
            factor_family="multi_factor",
            entry_rule="Require positive momentum confirmed by quality, volatility, and drawdown controls.",
            exit_rule="Sandbox 20 trading-day review; suggestions require later gate.",
            exit_horizon_days=20,
            risk_controls=["sector_concentration_check", "drawdown_floor", "quality_overlay", "crowding_risk_note"],
            pass_criteria=StrategyPassCriteria(
                min_sample_count=4,
                min_win_rate=0.55,
                min_average_return=0.012,
                max_drawdown_floor=-0.1,
            ),
            source_research_refs=["MSCI/PIMCO/Robeco factor research baseline", "Aegis Review System"],
            created_at=created,
        ),
        StrategyCandidate(
            strategy_id="portfolio_risk_veto_overlay",
            name="Portfolio risk veto overlay",
            market="US",
            universe="Portfolio-level overlay applied after candidate generation",
            factor_family="risk_overlay",
            entry_rule="Block or downgrade actions when portfolio exposure, concentration, or drawdown risk exceeds limits.",
            exit_rule="Review every daily brief; never places trades.",
            exit_horizon_days=1,
            risk_controls=["max_exposure_pct", "max_single_position_pct", "cash_buffer", "manual_execution_only"],
            pass_criteria=StrategyPassCriteria(
                min_sample_count=4,
                min_win_rate=0.5,
                min_average_return=0.0,
                max_drawdown_floor=-0.12,
            ),
            source_research_refs=["Aegis V2.0-A Portfolio Foundation", "Aegis V2.0-B Portfolio-Aware Brief"],
            created_at=created,
        ),
    ]


class StrategyCandidateLibrary:
    def __init__(self, path: Path):
        self.path = Path(path)

    def save(self, candidates: Iterable[StrategyCandidate]) -> dict:
        candidate_list = list(candidates)
        ids = [candidate.strategy_id for candidate in candidate_list]
        duplicates = sorted({strategy_id for strategy_id in ids if ids.count(strategy_id) > 1})
        if duplicates:
            raise StrategyLibraryError("duplicate strategy_id: " + ", ".join(duplicates))
        payload = {
            "schema_version": SCHEMA_VERSION,
            "updated_at": _now_iso(),
            "candidate_count": len(candidate_list),
            "candidates": [candidate.model_dump() for candidate in candidate_list],
            "safety": {
                "simulation_only": True,
                "no_real_trade": True,
                "no_broker_api": True,
                "no_webhook": True,
                "no_strategy_auto_mutation": True,
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload

    def load(self) -> list[StrategyCandidate]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise StrategyLibraryError("unsupported strategy library schema")
        return [StrategyCandidate(**item) for item in payload.get("candidates", [])]

    def get(self, strategy_id: str) -> StrategyCandidate:
        for candidate in self.load():
            if candidate.strategy_id == strategy_id:
                return candidate
        raise StrategyLibraryError(f"strategy_id not found: {strategy_id}")

    def list_by_market(self, market: str) -> list[StrategyCandidate]:
        return [candidate for candidate in self.load() if candidate.market == market]

    def list_by_factor_family(self, factor_family: str) -> list[StrategyCandidate]:
        return [candidate for candidate in self.load() if candidate.factor_family == factor_family]

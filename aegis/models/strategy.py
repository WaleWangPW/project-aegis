"""Strategy sandbox models for Project Aegis.

These models are intentionally separate from live RecommendationRecord and
PaperTrade models. They describe historical simulation inputs/outputs only;
they never imply real trading or broker execution.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Market = Literal["A", "H", "US"]
FactorFamily = Literal[
    "value",
    "quality",
    "momentum",
    "low_volatility",
    "dividend",
    "multi_factor",
    "risk_overlay",
]


class StrategyPassCriteria(BaseModel):
    min_sample_count: int = Field(ge=1)
    min_win_rate: float = Field(ge=0.0, le=1.0)
    min_average_return: float
    max_drawdown_floor: float = Field(
        description="Worst allowed drawdown. Example: -0.08 means no worse than -8%."
    )


class StrategyCandidate(BaseModel):
    strategy_id: str
    name: str
    market: Market
    universe: str
    factor_family: FactorFamily
    entry_rule: str
    exit_rule: str
    exit_horizon_days: int = Field(gt=0)
    risk_controls: list[str] = Field(default_factory=list)
    pass_criteria: StrategyPassCriteria
    source_research_refs: list[str] = Field(default_factory=list)
    created_at: str

    @field_validator("strategy_id", "name", "universe", "entry_rule", "exit_rule", "created_at")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value


class HistoricalStrategyCase(BaseModel):
    case_id: str
    strategy_id: str
    date: str
    symbol: str
    market: Market
    eligible: bool = True
    entry_price: float = Field(gt=0)
    exit_price: float = Field(gt=0)
    max_drawdown: float
    risk_flags: list[str] = Field(default_factory=list)
    factor_values: dict[str, float] = Field(default_factory=dict)
    evidence_ref: Optional[str] = None

    @field_validator("case_id", "strategy_id", "date", "symbol")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value

    @model_validator(mode="after")
    def _drawdown_must_be_non_positive(self) -> "HistoricalStrategyCase":
        if self.max_drawdown > 0:
            raise ValueError("max_drawdown must be zero or negative")
        return self


class StrategySandboxMetrics(BaseModel):
    strategy_id: str
    sample_count: int
    eligible_case_count: int
    win_rate: Optional[float]
    average_return: Optional[float]
    max_drawdown: Optional[float]
    turnover_proxy: Optional[float]
    exposure_count: int
    risk_flag_counts: dict[str, int] = Field(default_factory=dict)
    failed_reasons: list[str] = Field(default_factory=list)


class StrategySandboxResult(BaseModel):
    strategy_id: str
    status: Literal["PASS", "FAIL"]
    metrics: StrategySandboxMetrics
    safety: dict[str, bool]
    notes: list[str] = Field(default_factory=list)

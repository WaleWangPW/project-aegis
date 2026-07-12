"""FrozenContext — Phase 7 §5.1.

The single object that every backtest data access is checked against. Its
whole job is to make "no future data leakage" a structural property of the
code, not a promise kept by convention.

Date convention: per Master Spec §7.1, and consistent with every prior
phase in this codebase, `freeze_date` is a plain "YYYY-MM-DD" string (never
a `datetime.date` object) — see `PaperTradeService`'s module docstring
(Phase 6) for the same reasoning applied to `entry_date`/`as_of_date`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


class FutureDataAccessError(Exception):
    """Raised when decision-stage code attempts to read data that is only
    allowed during the evaluation stage (post-recommendation forward
    returns). A controlled, expected error — callers are not meant to let
    this crash a whole backtest range; `TimeTravelEngine` catches it per
    candidate/date and records it as a violation instead.
    """


@dataclass(frozen=True)
class FrozenContext:
    freeze_date: str  # "YYYY-MM-DD"
    session: str
    markets: list[str]
    stage: str = "decision"  # "decision" | "evaluation"
    lookahead_forbidden: bool = True

    def __post_init__(self) -> None:
        if self.stage not in ("decision", "evaluation"):
            raise ValueError(f"FrozenContext.stage must be 'decision' or 'evaluation', got {self.stage!r}")

    @property
    def allowed_data_max_date(self) -> str:
        """Alias matching the PHASE7 doc's suggested field name — same
        value as `freeze_date`, just named for readability at call sites
        that are specifically checking "how far can I read"."""
        return self.freeze_date

    def as_evaluation_stage(self) -> "FrozenContext":
        """Returns a new FrozenContext with `stage="evaluation"` — frozen
        dataclasses are immutable, so switching stages produces a new
        object rather than mutating this one out from under any code still
        holding a reference to the decision-stage context."""
        return replace(self, stage="evaluation")

    def is_decision_stage(self) -> bool:
        return self.stage == "decision"

    def is_evaluation_stage(self) -> bool:
        return self.stage == "evaluation"

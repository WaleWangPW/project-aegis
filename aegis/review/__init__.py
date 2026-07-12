"""Review — Phase 6 §5.4-5.5.

Post-hoc evaluation of a recommendation's *decision quality*, deliberately
kept separate from its raw return (Master Spec §8.9 docstring on
`ReviewRecord`) — a well-reasoned recommendation that loses money is not
automatically a bad decision.
"""

from __future__ import annotations

from aegis.review.repository import ReviewRepository
from aegis.review.service import ReviewService
from aegis.review.system import build_review_system_report, render_review_system_markdown

__all__ = [
    "ReviewRepository",
    "ReviewService",
    "build_review_system_report",
    "render_review_system_markdown",
]

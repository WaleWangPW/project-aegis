"""Real portfolio holdings and read-only portfolio snapshots."""

from aegis.portfolio.snapshot import (
    RiskBudget,
    build_portfolio_snapshot,
    render_portfolio_snapshot_markdown,
)
from aegis.portfolio.aware_brief import (
    build_portfolio_aware_brief,
    explain_recommendation_with_portfolio,
    render_portfolio_aware_brief_markdown,
)

__all__ = [
    "RiskBudget",
    "build_portfolio_snapshot",
    "build_portfolio_aware_brief",
    "explain_recommendation_with_portfolio",
    "render_portfolio_aware_brief_markdown",
    "render_portfolio_snapshot_markdown",
]

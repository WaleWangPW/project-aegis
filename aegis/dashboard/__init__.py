"""Dashboard JSON backend — Phase 5.

Generates `data/dashboard/dashboard_data.json`, schema-compatible with the
static `DATA` object already hard-coded in `dashboard/index.html`. That
HTML file is read for schema compatibility only — it is never modified by
this package.
"""

from .builder import DashboardBuilder
from .schema import (
    DashboardFocusItem,
    DashboardHoldingItem,
    DashboardMarketSnapshot,
    DashboardPaperTrading,
    DashboardPayload,
    DashboardRecommendationItem,
    validate_dashboard_payload,
)

__all__ = [
    "DashboardBuilder",
    "DashboardPayload",
    "DashboardMarketSnapshot",
    "DashboardRecommendationItem",
    "DashboardHoldingItem",
    "DashboardPaperTrading",
    "DashboardFocusItem",
    "validate_dashboard_payload",
]

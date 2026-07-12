"""ProviderCoverageReport — P1A §2.1.

A structured, honest report of what a `MarketDataProvider`-shaped object
actually supports, built by `aegis/data/provider_diagnostics.py` and
orchestrated by `aegis/data/live_validation.py`. This is diagnostic
tooling only — it is never consumed by Signal/Expert/Decision logic, and
a provider's availability here is never turned into a recommendation
(P1A hard-stop rule).

Date convention: plain "YYYY-MM-DD" strings / ISO-8601 datetimes, same as
every other model in this codebase.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

CheckStatus = Literal[
    "pass",
    "fail",
    "skipped",
    "unknown_empty",
    "unsupported",
    "permission_denied",
    "not_configured",
]
"""P1A.1 §1: hardened status vocabulary (Claude_Cowork_P1A1_PROVIDER_COVERAGE_RECONCILIATION.md).

- "pass": the call succeeded, returned at least one row, and (for checks
  that are cross-market reconciled) was not flagged as a suspected
  duplicate of another market's result.
- "fail": the call raised a `ProviderError` whose message does not look
  permission/entitlement related — an unexplained real provider failure.
- "skipped": the provider object doesn't implement this method at all
  (`AttributeError` degrade).
- "unknown_empty": the call succeeded but returned an empty result — does
  NOT confirm coverage either way (was simply "unknown" pre-P1A.1;
  renamed for clarity, same meaning).
- "unsupported": the call succeeded and returned rows, but those rows are
  suspected to not actually be this market's data (e.g. a non-A market's
  `stock_basic` check returning the exact same row count as A股's) —
  never trust this as confirmed coverage.
- "permission_denied": the call raised a `ProviderError` whose message
  contains a permission/entitlement/quota keyword — a real failure, just
  a more specific, actionable category than plain "fail".
- "not_configured": the check was never attempted because a required
  input (e.g. a per-market sample symbol) has no configured value.
"""


class ProviderCheck(BaseModel):
    check_name: str
    market: Optional[str] = None
    data_type: str
    status: CheckStatus
    sample_symbol: Optional[str] = None
    rows_returned: Optional[int] = None
    warning: Optional[str] = None
    data_gap_id: Optional[str] = None


class CoverageSummary(BaseModel):
    pass_count: int = 0
    fail_count: int = 0
    skipped_count: int = 0
    unknown_count: int = 0
    unsupported_count: int = 0
    permission_denied_count: int = 0
    not_configured_count: int = 0
    critical_gaps: list[str] = Field(default_factory=list)


class ProviderCoverageReport(BaseModel):
    run_id: str
    created_at: str
    provider: str
    token_present: bool
    network_available: bool
    checks: list[ProviderCheck] = Field(default_factory=list)
    summary: CoverageSummary = Field(default_factory=CoverageSummary)

    def write_json(self, path: str | Path) -> Path:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(self.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path


def summarize_checks(checks: list[ProviderCheck]) -> CoverageSummary:
    """Pure aggregation — no fabrication, just tallying already-honest
    per-check statuses. `critical_gaps` lists the check_name of every
    `status in ("fail", "permission_denied")` check — a real, unexplained
    or entitlement-related provider failure — as opposed to
    `skipped`/`unknown_empty`/`unsupported`/`not_configured`, which are
    softer, expected/structural degrade states that are still recorded
    (never hidden) but are not "critical" in the same sense."""
    summary = CoverageSummary()
    for check in checks:
        if check.status == "pass":
            summary.pass_count += 1
        elif check.status == "fail":
            summary.fail_count += 1
            summary.critical_gaps.append(check.check_name)
        elif check.status == "skipped":
            summary.skipped_count += 1
        elif check.status == "unknown_empty":
            summary.unknown_count += 1
        elif check.status == "unsupported":
            summary.unsupported_count += 1
        elif check.status == "permission_denied":
            summary.permission_denied_count += 1
            summary.critical_gaps.append(check.check_name)
        elif check.status == "not_configured":
            summary.not_configured_count += 1
    return summary

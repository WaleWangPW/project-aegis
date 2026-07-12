"""DataGapRegistry — Master Spec §10.1 / Phase 1 §4.4.

Records every missing/degraded data situation explicitly instead of
silently proceeding — a data gap is a first-class, auditable fact, not a
swallowed exception (Master Spec §4: "Missing data: null + data_quality /
DataGap, 禁止编造").
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from aegis.utils.jsonl import append_jsonl, read_jsonl

SEVERITIES = {"info", "warning", "error"}


class DataGapRegistry:
    def __init__(self, records_path: str | Path):
        self.records_path = Path(records_path)

    def record_gap(
        self,
        *,
        date: str,
        market: Optional[str],
        symbol: Optional[str],
        provider: str,
        data_type: str,
        severity: str,
        message: str,
        consumer_impact: Optional[list[str]] = None,
    ) -> dict:
        if severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(SEVERITIES)}, got {severity!r}")

        id_parts = ["gap", date.replace("-", "")]
        if market:
            id_parts.append(market)
        if symbol:
            id_parts.append(symbol)
        id_parts.append(data_type)

        gap = {
            "gap_id": "_".join(id_parts),
            "date": date,
            "market": market,
            "symbol": symbol,
            "provider": provider,
            "data_type": data_type,
            "severity": severity,
            "message": message,
            "consumer_impact": consumer_impact or [],
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        }
        append_jsonl(self.records_path, gap)
        return gap

    def list_gaps(self) -> list[dict]:
        return list(read_jsonl(self.records_path))

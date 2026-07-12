"""Signal — Master Spec §8.4.

A single, uniformly-shaped computed signal (trend, volume, relative
strength, sector, fundamental, risk — see Master Spec §12.1).
Produced by: aegis.signals.* (Phase 3).
Consumed by: Expert Agents, Review, Strategy Lab (later phases).
Storage: data/processed/YYYY-MM-DD/signals_*.json, optionally
data/records/signals.jsonl.

Acceptance: when data is missing, evidence_strength must be "unknown" —
the signal must never crash and must never fabricate a value.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel

SignalType = Literal["trend", "volume", "relative_strength", "sector", "fundamental", "risk"]
EvidenceStrength = Literal["strong", "moderate", "weak", "unknown"]


class Signal(BaseModel):
    signal_id: str
    signal_name: str
    signal_type: SignalType
    symbol: str
    market: str
    date: str
    value: Optional[Any] = None
    interpretation: str
    evidence_strength: EvidenceStrength
    data_source: str
    lookback_window: Optional[str] = None
    valid_until: Optional[str] = None

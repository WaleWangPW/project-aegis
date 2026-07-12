"""SectorSignal — Phase 3 §5.2: sector presence / sector in market rotation
list. Missing sector => unknown.
"""

from __future__ import annotations

from aegis.signals.base import BaseSignal, SignalContext
from aegis.models.signal import Signal


class SectorSignal(BaseSignal):
    name = "sector_rotation_presence"
    signal_type = "sector"

    def compute(self, context: SignalContext) -> Signal:
        sector = context.candidate.sector if context.candidate is not None else None
        if not sector:
            return self._unknown(
                context,
                reason="No sector classification available for this candidate.",
                data_source="stock_basic",
            )

        rotation = list(context.market_snapshot.sector_rotation) if context.market_snapshot else []
        in_rotation = sector in rotation if rotation else False

        value = {"sector": sector, "in_rotation": in_rotation, "sector_rotation_list": rotation}
        if rotation:
            evidence_strength = "moderate"
            interpretation = (
                f"Sector '{sector}' is {'in' if in_rotation else 'not in'} the current sector_rotation list."
            )
        else:
            evidence_strength = "weak"
            interpretation = (
                f"Sector '{sector}' known, but MarketSnapshot has no sector_rotation data to compare against."
            )

        return self._signal(
            context,
            value=value,
            interpretation=interpretation,
            evidence_strength=evidence_strength,
            data_source="market_snapshot",
        )

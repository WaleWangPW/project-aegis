"""FundamentalSignal — Phase 3 §5.2: fundamental data presence,
valuation/fundamental placeholder interpretation. No complex finance model
in P0 — this only reports presence and any explicit risk_flags the caller
supplied, it never computes valuation ratios itself.
"""

from __future__ import annotations

from aegis.signals.base import BaseSignal, SignalContext
from aegis.models.signal import Signal


class FundamentalSignal(BaseSignal):
    name = "fundamental_presence"
    signal_type = "fundamental"

    def compute(self, context: SignalContext) -> Signal:
        fundamentals = context.fundamentals
        if not fundamentals:
            return self._unknown(
                context,
                reason="No fundamental data available for this candidate.",
                data_source="tushare",
            )

        risk_flags = list(fundamentals.get("risk_flags") or [])
        value = {"has_data": True, "keys": sorted(fundamentals.keys()), "risk_flags": risk_flags}

        if risk_flags:
            interpretation = (
                f"Fundamental data present but flags risk(s): {', '.join(risk_flags)}. "
                "No complex financial model applied (P0 placeholder)."
            )
        else:
            interpretation = (
                "Fundamental data present, no explicit risk flags. "
                "No complex financial model applied (P0 placeholder)."
            )

        # Deliberately never "strong"/"moderate": this is presence-only P0
        # evidence, not a real fundamental analysis.
        return self._signal(
            context,
            value=value,
            interpretation=interpretation,
            evidence_strength="weak",
            data_source="tushare",
        )

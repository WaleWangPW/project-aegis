"""Decision Engine — Phase 4 §5-7.

`compute_decision_confidence` (decision-reliability metadata, never stock
attractiveness) + `DecisionEngine` (evidence-voting Watch/Ready/Action/Exit
assignment, Risk veto + Timing oppose + market downgrade hard rules).
"""

from .confidence import compute_decision_confidence
from .engine import DecisionEngine

__all__ = ["compute_decision_confidence", "DecisionEngine"]

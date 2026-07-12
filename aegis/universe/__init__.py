"""Universe package — Phase 2 (Candidate generation).

`filters.py` holds pure, stateless filter predicates; `builder.py` holds
`UniverseBuilder`, the orchestration class that turns a stock list plus
holdings into a `list[Candidate]`. No scoring, no LLM.
"""

from .builder import UniverseBuilder

__all__ = ["UniverseBuilder"]

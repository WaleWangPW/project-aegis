"""PaperTradeRepository — Phase 6 §5.2.

Append-only JSONL persistence, same pattern as `RecommendationRepository`
(Phase 4) and `DataGapRegistry` (Phase 1) — no database. Updates (e.g.
attaching a newly-due horizon return, or closing a trade) use a safe
read-all/rewrite-all via the existing `write_jsonl` helper rather than
in-place file editing, since JSONL has no native "update a row" operation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from aegis.models.paper_trade import PaperTrade
from aegis.utils.jsonl import append_jsonl, read_jsonl, write_jsonl

PAPER_TRADES_FILENAME = "paper_trades.jsonl"


class PaperTradeRepository:
    def __init__(self, records_dir: str | Path):
        self.records_dir = Path(records_dir)
        self.path = self.records_dir / PAPER_TRADES_FILENAME

    def append(self, trade: PaperTrade) -> None:
        append_jsonl(self.path, trade.model_dump())

    def list_all(self) -> list[PaperTrade]:
        # read_jsonl parses every line as JSON and lets a malformed line
        # raise json.JSONDecodeError rather than silently skipping/
        # corrupting it (PHASE6 doc §5.2: "never silently corrupt invalid
        # JSONL lines").
        return [PaperTrade(**row) for row in read_jsonl(self.path)]

    def list_open(self) -> list[PaperTrade]:
        return [t for t in self.list_all() if t.status == "open"]

    def find_by_id(self, paper_trade_id: str) -> Optional[PaperTrade]:
        for trade in self.list_all():
            if trade.paper_trade_id == paper_trade_id:
                return trade
        return None

    def find_by_recommendation_id(self, recommendation_id: str) -> list[PaperTrade]:
        return [t for t in self.list_all() if t.recommendation_id == recommendation_id]

    def save_all(self, trades: list[PaperTrade]) -> None:
        write_jsonl(self.path, [t.model_dump() for t in trades])

    def update(self, trade: PaperTrade) -> None:
        """Safe rewrite: replace the row with a matching `paper_trade_id`
        (or append it, if it isn't present yet) and rewrite the whole file.
        """
        all_trades = self.list_all()
        for i, existing in enumerate(all_trades):
            if existing.paper_trade_id == trade.paper_trade_id:
                all_trades[i] = trade
                break
        else:
            all_trades.append(trade)
        self.save_all(all_trades)

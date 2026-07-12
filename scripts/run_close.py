#!/usr/bin/env python3
"""run_close.py — Phase 6 §5.7.

The end-of-day counterpart to `run_pre_market.py`:

    Load config
    -> update open PaperTrades (forward returns / max drawdown, as of --date)
    -> generate due ReviewRecords
    -> save minimal InvestmentMemory lessons from those reviews
    -> rebuild data/dashboard/dashboard_data.json via the existing
       DashboardBuilder (never modifies dashboard/index.html)

Never places a real trade, never talks to a broker, never fabricates a
price/return/review. Exits 0 with an honest empty summary when there are no
open PaperTrades yet (e.g. before any Action recommendation has been made).

Usage:
    python scripts/run_close.py --date 2026-07-03
    python scripts/run_close.py --date 2026-07-03 --data-dir data
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.dashboard.builder import DashboardBuilder  # noqa: E402
from aegis.data.cache import DataCache  # noqa: E402
from aegis.data.gaps import DataGapRegistry  # noqa: E402
from aegis.data.tushare_adapter import TushareAdapter  # noqa: E402
from aegis.market.service import MarketDataService  # noqa: E402
from aegis.memory.repository import MemoryRepository  # noqa: E402
from aegis.memory.service import MemoryService  # noqa: E402
from aegis.models.investment_memory import InvestmentMemory  # noqa: E402
from aegis.models.paper_trade import PaperTrade  # noqa: E402
from aegis.models.review import ReviewRecord  # noqa: E402
from aegis.paper.repository import PaperTradeRepository  # noqa: E402
from aegis.paper.service import PaperTradeService  # noqa: E402
from aegis.recommendation.repository import RecommendationRepository  # noqa: E402
from aegis.review.repository import ReviewRepository  # noqa: E402
from aegis.review.service import ReviewService  # noqa: E402


@dataclass
class CloseResult:
    date: str
    updated_trades: list[PaperTrade] = field(default_factory=list)
    generated_reviews: list[ReviewRecord] = field(default_factory=list)
    created_memories: list[InvestmentMemory] = field(default_factory=list)
    dashboard_path: Optional[Path] = None
    dashboard_error: Optional[str] = None


def run_close(
    *,
    date: str,
    repo_root: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    provider: Optional[Any] = None,
) -> CloseResult:
    """Testable core logic behind the CLI. `provider` is injectable so
    tests never touch real Tushare/network, same pattern as
    `run_pre_market.run_pre_market`."""
    root = repo_root or Path(__file__).resolve().parents[1]
    config_dir = root / "config"
    resolved_data_dir = data_dir or (root / "data")
    records_dir = resolved_data_dir / "records"

    adapter = provider if provider is not None else TushareAdapter.from_env()
    cache = DataCache(resolved_data_dir / "cache")
    gaps = DataGapRegistry(records_dir / "data_gaps.jsonl")
    market_data_service = MarketDataService(provider=adapter, cache=cache, gaps=gaps)

    paper_repository = PaperTradeRepository(records_dir)
    paper_service = PaperTradeService(
        repository=paper_repository, market_data_service=market_data_service, gaps=gaps
    )
    updated_trades = paper_service.update_open_trades(date)

    recommendation_repository = RecommendationRepository(records_dir)
    review_repository = ReviewRepository(records_dir)
    review_service = ReviewService(
        review_repository=review_repository,
        paper_repository=paper_repository,
        recommendation_repository=recommendation_repository,
        records_dir=records_dir,
    )
    generated_reviews = review_service.generate_due_reviews(date)

    memory_repository = MemoryRepository(records_dir)
    memory_service = MemoryService(repository=memory_repository)
    created_memories: list[InvestmentMemory] = []
    for review in generated_reviews:
        memories = memory_service.create_from_review(review)
        if memories:
            memory_service.append_memories(memories)
            created_memories.extend(memories)

    dashboard_path: Optional[Path] = None
    dashboard_error: Optional[str] = None
    try:
        dashboard_builder = DashboardBuilder(
            records_dir=records_dir,
            holdings_config_path=config_dir / "holdings.yaml",
            output_path=resolved_data_dir / "dashboard" / "dashboard_data.json",
        )
        dashboard_payload = dashboard_builder.build(date=date, session="pre_market")
        dashboard_path = dashboard_builder.write_json(dashboard_payload)
    except Exception as exc:  # noqa: BLE001 - deliberate, reported on the result
        dashboard_error = f"{type(exc).__name__}: {exc}"

    return CloseResult(
        date=date,
        updated_trades=updated_trades,
        generated_reviews=generated_reviews,
        created_memories=created_memories,
        dashboard_path=dashboard_path,
        dashboard_error=dashboard_error,
    )


def _print_summary(result: CloseResult) -> None:
    print("Project Aegis run_close Phase 6")
    print(f"date: {result.date}")
    print(f"updated_trades: {len(result.updated_trades)}")
    print(f"generated_reviews: {len(result.generated_reviews)}")
    print(f"created_memories: {len(result.created_memories)}")
    if not result.updated_trades:
        print("No open PaperTrades to update (none exist yet, or all are already closed).")
    if not result.generated_reviews:
        print("No reviews newly due as of this date.")
    if result.dashboard_error:
        print(f"dashboard_build: FAILED ({result.dashboard_error})")
    elif result.dashboard_path is not None:
        print(f"dashboard_build: {result.dashboard_path}")
    print("Phase 6 close complete. No Time Travel Backtest generated in this phase.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Project Aegis Phase 6 end-of-day close pipeline.")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--data-dir", default=None, help="Override the data/ directory (default: <repo_root>/data)")
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir) if args.data_dir else None
    result = run_close(date=args.date, data_dir=data_dir)
    _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

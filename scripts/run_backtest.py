#!/usr/bin/env python3
"""run_backtest.py — Phase 7 §7.

CLI wrapper around `TimeTravelEngine.run_range(...)`. Never places a real
trade, never talks to a broker. Writes backtest output only under the
isolated `data/processed/backtests/<run_id>/` directory — never
`data/records/`.

Usage:
    python scripts/run_backtest.py --start 2026-01-01 --end 2026-01-31 --markets A,US
    python scripts/run_backtest.py --start 2026-01-01 --end 2026-01-31 --markets A,H,US --session close
    python scripts/run_backtest.py --start 2026-01-01 --end 2026-01-31 --markets US --data-dir data
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.backtest.models import BacktestResult, MetricsReport  # noqa: E402
from aegis.backtest.repository import BacktestRepository  # noqa: E402
from aegis.backtest.time_travel import TimeTravelEngine  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_MARKETS = {"A", "H", "US"}


class BacktestArgumentError(ValueError):
    """A controlled, expected CLI input error (bad date range/markets) —
    never a raw traceback."""


def _validate_date_range(start: str, end: str) -> None:
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
    except ValueError as exc:
        raise BacktestArgumentError(f"--start {start!r} is not a valid YYYY-MM-DD date.") from exc
    try:
        end_dt = datetime.strptime(end, "%Y-%m-%d")
    except ValueError as exc:
        raise BacktestArgumentError(f"--end {end!r} is not a valid YYYY-MM-DD date.") from exc
    if end_dt < start_dt:
        raise BacktestArgumentError(f"--end {end!r} is before --start {start!r}.")


def _validate_markets(markets: list[str]) -> None:
    if not markets:
        raise BacktestArgumentError("--markets must name at least one market.")
    unknown = [m for m in markets if m not in VALID_MARKETS]
    if unknown:
        raise BacktestArgumentError(
            f"Unknown market(s) {unknown} — valid markets are {sorted(VALID_MARKETS)}."
        )


def _generate_run_id() -> str:
    return f"bt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"


def render_metrics_markdown(report: MetricsReport) -> str:
    lines = [
        f"# Project Aegis Backtest Metrics — {report.run_id}",
        "",
        f"- Date range: {report.start_date} -> {report.end_date}",
        f"- Trading days processed: {report.trading_days_run}",
        f"- Total recommendations: {report.total_recommendations}",
        f"  - Action: {report.action_count}",
        f"  - Ready: {report.ready_count}",
        f"  - Watch: {report.watch_count}",
        f"  - Exit: {report.exit_count}",
        "",
        "## Action success rate by horizon",
        "",
    ]
    for key, value in (
        ("5d", report.action_success_rate_5d),
        ("10d", report.action_success_rate_10d),
        ("20d", report.action_success_rate_20d),
        ("40d", report.action_success_rate_40d),
    ):
        lines.append(f"- {key}: {value if value is not None else 'DATA_GAP: 无可用数据'}")

    lines.append("")
    lines.append("## Average return by horizon")
    lines.append("")
    for key, value in report.average_return_by_horizon.items():
        lines.append(f"- {key}: {value if value is not None else 'DATA_GAP: 无可用数据'}")

    lines.append("")
    lines.append("## Max drawdown summary")
    lines.append("")
    lines.append(f"- {report.max_drawdown_summary}")

    lines.append("")
    lines.append("## Market breakdown")
    lines.append("")
    if report.market_breakdown:
        for market, stats in report.market_breakdown.items():
            lines.append(f"- {market}: {stats}")
    else:
        lines.append("- DATA_GAP: no recommendations in this range")

    lines.append("")
    lines.append("## Sector breakdown")
    lines.append("")
    if report.sector_breakdown:
        for sector, stats in report.sector_breakdown.items():
            lines.append(f"- {sector}: {stats}")
    else:
        lines.append("- DATA_GAP: no recommendations in this range")

    lines.append("")
    lines.append(f"Data gaps: {report.data_gap_count}")
    lines.append(f"No future data violations: {report.no_future_data_violations}")
    lines.append("")
    lines.append(report.summary)
    lines.append("")
    return "\n".join(lines)


def run_backtest(
    *,
    start: str,
    end: str,
    markets: list[str],
    session: str = "close",
    data_dir: Path,
    repo_root: Path,
    base_provider=None,
    run_id: Optional[str] = None,
) -> tuple[str, list[BacktestResult], MetricsReport, Path]:
    """Testable core logic behind the CLI. Raises `BacktestArgumentError`
    on invalid input; never touches real network in tests since
    `base_provider` is injectable, same pattern as every other Phase
    2-6 script in this project."""
    _validate_date_range(start, end)
    _validate_markets(markets)

    run_id = run_id or _generate_run_id()
    engine = TimeTravelEngine(base_provider=base_provider, data_dir=str(data_dir), repo_root=str(repo_root))
    results = engine.run_range(start_date=start, end_date=end, session=session, markets=markets, run_id=run_id)
    report = engine.build_metrics_report(results)

    output_dir = data_dir / "processed" / "backtests" / run_id
    repository = BacktestRepository(output_dir)
    for result in results:
        repository.append_result(result)
    markdown = render_metrics_markdown(report)
    repository.write_metrics_report(report, markdown)
    repository.append_access_log_entries(engine.access_log)

    return run_id, results, report, output_dir


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Project Aegis Phase 7 Time Travel Backtest.")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--markets", default="A,H,US", help="Comma-separated, e.g. A,H,US")
    parser.add_argument("--session", default="close")
    parser.add_argument("--data-dir", default=str(REPO_ROOT / "data"))
    args = parser.parse_args(argv)

    markets = [m.strip() for m in args.markets.split(",") if m.strip()]

    try:
        run_id, results, report, output_dir = run_backtest(
            start=args.start,
            end=args.end,
            markets=markets,
            session=args.session,
            data_dir=Path(args.data_dir),
            repo_root=REPO_ROOT,
        )
    except BacktestArgumentError as exc:
        print(f"Backtest argument error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - controlled, never a raw traceback; never prints secrets
        print(f"Backtest run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    total_recommendations = sum(len(r.recommendations) for r in results)
    violations = sum(r.no_future_data_violations for r in results)

    print(f"Backtest run_id: {run_id}")
    print(f"Date range: {args.start} -> {args.end}")
    print(f"Markets: {','.join(markets)}")
    print(f"Trading days processed: {len(results)}")
    print(f"Recommendations: {total_recommendations}")
    print(f"No future data violations: {violations}")
    print(f"Output: {output_dir}/")

    return 0 if violations == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Phase 7 tests for aegis/backtest/metrics.py — PHASE7 doc §5.5/§9.4.

Pure functions over `list[BacktestResult]` — no fake providers needed,
just directly constructed `BacktestResult` objects. No composite/weighted
scoring anywhere in this module (ADR-002) — only counts and averages.
"""

from __future__ import annotations

from aegis.backtest.metrics import (
    compute_action_success_rate,
    compute_average_return_by_horizon,
    compute_data_gap_count,
    compute_market_breakdown,
    compute_max_drawdown_summary,
    compute_no_future_data_violations,
    compute_sector_breakdown,
    compute_status_counts,
)
from aegis.backtest.models import BacktestResult


def _rec(rec_id: str, status: str, market: str = "US", sector: str | None = "Tech") -> dict:
    return {"recommendation_id": rec_id, "status": status, "market": market, "sector": sector}


def _result(
    *,
    run_id: str = "bt_1",
    freeze_date: str = "2026-06-30",
    recommendations: list[dict] | None = None,
    forward_returns: dict | None = None,
    data_gaps: list[dict] | None = None,
    no_future_data_violations: int = 0,
) -> BacktestResult:
    return BacktestResult(
        run_id=run_id,
        freeze_date=freeze_date,
        session="close",
        markets=["US"],
        recommendation_ids=[r["recommendation_id"] for r in (recommendations or [])],
        recommendations=recommendations or [],
        forward_returns=forward_returns or {},
        data_gaps=data_gaps or [],
        no_future_data_violations=no_future_data_violations,
        created_at="2026-06-30T00:00:00+00:00",
    )


def test_compute_status_counts_tallies_watch_ready_action_exit():
    results = [
        _result(
            recommendations=[
                _rec("r1", "Watch"),
                _rec("r2", "Ready"),
                _rec("r3", "Action"),
                _rec("r4", "Exit"),
                _rec("r5", "Action"),
            ]
        )
    ]
    counts = compute_status_counts(results)
    assert counts == {"Watch": 1, "Ready": 1, "Action": 2, "Exit": 1}


def test_compute_action_success_rate_only_counts_action_recommendations():
    results = [
        _result(
            recommendations=[_rec("r1", "Action"), _rec("r2", "Watch")],
            forward_returns={
                "r1": {"5d": 0.10, "10d": None, "20d": None, "40d": None, "max_drawdown": -0.02, "status": "complete"},
                "r2": {"5d": -0.50, "10d": None, "20d": None, "40d": None, "max_drawdown": -0.5, "status": "complete"},
            },
        )
    ]
    # Only r1 (Action) counts; r2 is Watch and must be excluded even though
    # its 5d return is very negative.
    rate = compute_action_success_rate(results, "5d")
    assert rate == 1.0


def test_compute_action_success_rate_is_none_when_no_horizon_resolves():
    results = [
        _result(
            recommendations=[_rec("r1", "Action")],
            forward_returns={"r1": {"5d": None, "10d": None, "20d": None, "40d": None, "status": "data_gap"}},
        )
    ]
    assert compute_action_success_rate(results, "5d") is None


def test_compute_average_return_by_horizon_averages_across_results():
    results = [
        _result(
            recommendations=[_rec("r1", "Action")],
            forward_returns={"r1": {"5d": 0.10, "10d": None, "20d": None, "40d": None}},
        ),
        _result(
            recommendations=[_rec("r2", "Action")],
            forward_returns={"r2": {"5d": 0.30, "10d": None, "20d": None, "40d": None}},
        ),
    ]
    averages = compute_average_return_by_horizon(results)
    assert averages["5d"] == 0.20
    assert averages["10d"] is None


def test_compute_max_drawdown_summary_reports_worst_case():
    results = [
        _result(forward_returns={"r1": {"max_drawdown": -0.05}}),
        _result(forward_returns={"r2": {"max_drawdown": -0.30}}),
    ]
    summary = compute_max_drawdown_summary(results)
    assert summary["worst"] == -0.30
    assert summary["count"] == 2


def test_compute_max_drawdown_summary_empty_when_no_data():
    assert compute_max_drawdown_summary([]) == {"worst": None, "count": 0}


def test_compute_market_breakdown_aggregates_per_market():
    results = [
        _result(recommendations=[_rec("r1", "Action", market="US"), _rec("r2", "Watch", market="A")]),
        _result(recommendations=[_rec("r3", "Action", market="US")]),
    ]
    breakdown = compute_market_breakdown(results)
    assert breakdown["US"] == {"count": 2, "action_count": 2}
    assert breakdown["A"] == {"count": 1, "action_count": 0}


def test_compute_sector_breakdown_aggregates_per_sector():
    results = [_result(recommendations=[_rec("r1", "Action", sector="Fintech"), _rec("r2", "Watch", sector=None)])]
    breakdown = compute_sector_breakdown(results)
    assert breakdown["Fintech"] == {"count": 1, "action_count": 1}
    assert breakdown["未知行业"] == {"count": 1, "action_count": 0}


def test_compute_data_gap_count_sums_across_results():
    results = [
        _result(data_gaps=[{"a": 1}, {"b": 2}]),
        _result(data_gaps=[{"c": 3}]),
    ]
    assert compute_data_gap_count(results) == 3


def test_compute_no_future_data_violations_sums_across_results():
    results = [_result(no_future_data_violations=1), _result(no_future_data_violations=2)]
    assert compute_no_future_data_violations(results) == 3


def test_metrics_never_produce_a_single_composite_score():
    # Guard against ADR-002 regression: no *function* in this module should
    # be named/shaped like a weighted composite score (the module's own
    # docstring legitimately mentions "no composite scoring" in prose, so
    # this checks function names, not the whole file's text).
    import inspect

    import aegis.backtest.metrics as metrics_module

    forbidden_terms = ("composite", "weighted_score", "overall_score")
    function_names = [name.lower() for name, obj in inspect.getmembers(metrics_module, inspect.isfunction)]
    for term in forbidden_terms:
        assert not any(term in name for name in function_names)

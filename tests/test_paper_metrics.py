"""Phase 6 tests for aegis/paper/metrics.py — PHASE6 doc §5.3/§7.1.6."""

from __future__ import annotations

from aegis.paper.metrics import compute_horizon_return, compute_max_drawdown, compute_return


def test_compute_return_basic():
    assert round(compute_return(100.0, 105.2), 4) == 0.052


def test_compute_return_negative():
    assert round(compute_return(100.0, 90.0), 4) == -0.10


def test_compute_return_missing_input_returns_none():
    assert compute_return(None, 105.0) is None
    assert compute_return(100.0, None) is None
    assert compute_return(None, None) is None


def test_compute_return_zero_entry_returns_none():
    assert compute_return(0.0, 105.0) is None


def test_compute_return_invalid_type_returns_none():
    assert compute_return("not-a-number", 105.0) is None


def test_compute_max_drawdown_basic():
    # Peak at 110 (index 1), trough at 88 (index 3) -> (88-110)/110
    series = [100.0, 110.0, 95.0, 88.0, 100.0]
    dd = compute_max_drawdown(series)
    assert round(dd, 4) == round((88.0 - 110.0) / 110.0, 4)


def test_compute_max_drawdown_monotonic_up_is_zero():
    series = [100.0, 105.0, 110.0, 120.0]
    assert compute_max_drawdown(series) == 0.0


def test_compute_max_drawdown_empty_or_none_returns_none():
    assert compute_max_drawdown([]) is None
    assert compute_max_drawdown(None) is None
    assert compute_max_drawdown([None, None]) is None


def test_compute_max_drawdown_skips_none_entries():
    series = [100.0, None, 110.0, None, 88.0]
    dd = compute_max_drawdown(series)
    assert round(dd, 4) == round((88.0 - 110.0) / 110.0, 4)


def test_compute_horizon_return_matches_compute_return():
    assert compute_horizon_return(100.0, 105.2) == compute_return(100.0, 105.2)


def test_compute_horizon_return_missing_input_returns_none():
    assert compute_horizon_return(None, 105.0) is None

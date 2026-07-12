from __future__ import annotations

import argparse

import scripts.run_stock_agent_a_share_strategy_cycle as cycle


def test_explicit_dragon_tiger_overrides_are_injected_into_collect_command():
    args = argparse.Namespace(
        dragon_tiger_lookback_dates=90,
        dragon_tiger_forward_days=20,
        dragon_tiger_max_symbols=24,
        dragon_tiger_max_events_per_symbol=3,
    )

    dynamic_args = cycle.explicit_dragon_tiger_args(args)
    argv, source = cycle.command_argv(
        {
            "name": "collect_a_share_dragon_tiger_research_samples",
            "argv": ["scripts/collect_a_share_dragon_tiger_research_samples.py"],
        },
        dragon_tiger_args=dynamic_args,
    )

    assert source == "explicit_override"
    assert argv == [
        "scripts/collect_a_share_dragon_tiger_research_samples.py",
        "--lookback-dates",
        "90",
        "--forward-days",
        "20",
        "--max-symbols",
        "24",
        "--max-events-per-symbol",
        "3",
    ]


def test_partial_dragon_tiger_override_is_rejected():
    args = argparse.Namespace(
        dragon_tiger_lookback_dates=90,
        dragon_tiger_forward_days=None,
        dragon_tiger_max_symbols=24,
        dragon_tiger_max_events_per_symbol=3,
    )

    try:
        cycle.explicit_dragon_tiger_args(args)
    except ValueError as exc:
        assert "positive integers" in str(exc)
    else:
        raise AssertionError("partial dragon-tiger override should fail")

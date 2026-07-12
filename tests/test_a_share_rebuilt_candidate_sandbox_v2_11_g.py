from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.a_share_rebuilt_candidate_sandbox import (
    build_a_share_rebuilt_candidate_sandbox_report,
    build_expanded_retest_cases,
)
import scripts.validate_v2_11_g_a_share_rebuilt_candidate_sandbox_dry_run as validator


def _source_c(cache_dir: Path) -> dict:
    return {
        "overall_status": "PASS",
        "source_historical_cache_dir": str(cache_dir),
        "live_data_source": {"provider": "tushare", "market": "A"},
        "candidates": [
            {
                "strategy_id": "strategy_a_low_vol_dividend_defensive",
                "name": "A-share low-volatility dividend defensive sandbox candidate",
                "market": "A",
                "universe": "A-share liquid large/mid cap universe.",
                "factor_family": "risk_overlay",
                "entry_rule": "rank by dividend yield sustainability",
                "exit_rule": "20 trading-day sandbox review",
                "exit_horizon_days": 20,
                "risk_controls": ["liquidity_filter", "risk_veto"],
                "pass_criteria": {
                    "min_sample_count": 4,
                    "min_win_rate": 0.5,
                    "min_average_return": 0.008,
                    "max_drawdown_floor": -0.08,
                },
                "source_research_refs": ["source_a"],
                "created_at": "2026-07-11T00:00:00+08:00",
            }
        ],
    }


def _source_f() -> dict:
    return {
        "overall_status": "PASS",
        "rebuild_proposals": [
            {
                "proposal_id": "rebuild_strategy_a_low_vol_dividend_defensive",
                "source_strategy_id": "strategy_a_low_vol_dividend_defensive",
                "market": "A",
                "source_symbols": ["600000.SH", "601318.SH", "000001.SZ", "600519.SH"],
                "rebuild_actions": [
                    "add_market_regime_filter",
                    "tighten_drawdown_and_volatility_filter",
                    "expand_historical_sample_before_retest",
                ],
                "retest_requirements": {"minimum_total_sample_count": 24, "minimum_window_count": 6},
                "requires_sandbox": True,
                "requires_suggestion_gate": True,
                "auto_applied": False,
                "user_facing_suggestion_allowed": False,
                "blocked_until_sandbox_pass": True,
            }
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _make_cache(cache_dir: Path) -> None:
    symbols = ["600000.SH", "601318.SH", "000001.SZ", "600519.SH"]
    dates = [f"202401{i + 1:02d}" for i in range(140)]
    _write_json(cache_dir / "trade_calendar.json", {"open_dates": dates})
    daily_dir = cache_dir / "daily_by_trade_date"
    daily_dir.mkdir(parents=True, exist_ok=True)
    for idx, date in enumerate(dates):
        rows = []
        for symbol_index, symbol in enumerate(symbols):
            base = 100.0 + symbol_index
            close = base - (idx * 0.03)
            rows.append(
                {
                    "ts_code": symbol,
                    "trade_date": date,
                    "open": close,
                    "high": close + 0.2,
                    "low": close - 9.5,
                    "close": close,
                    "vol": 1000000,
                    "amount": 1000000,
                }
            )
        _write_json(daily_dir / f"{date}.json", {"rows": rows})


def test_v2_11_g_builds_expanded_retest_cases(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    _make_cache(cache_dir)

    cases = build_expanded_retest_cases(source_v2_11_f=_source_f(), cache_dir=cache_dir)

    assert len(cases) == 24
    assert {case.symbol for case in cases} == {"600000.SH", "601318.SH", "000001.SZ", "600519.SH"}
    assert all(case.evidence_ref and case.evidence_ref.startswith("tushare_cache:") for case in cases)


def test_v2_11_g_report_keeps_a_share_blocked_when_expanded_sandbox_fails(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    _make_cache(cache_dir)

    report = build_a_share_rebuilt_candidate_sandbox_report(
        source_v2_11_c=_source_c(cache_dir),
        source_v2_11_f=_source_f(),
        cache_dir=cache_dir,
        run_id="v2_11_g_unit",
        evidence_refs=["c.json", "f.json"],
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["expanded_case_count"] == 24
    assert report["summary"]["strategy_pass_count"] == 0
    assert report["summary"]["strategy_fail_count"] == 1
    assert report["summary"]["a_share_reentry_allowed"] is False
    assert report["checks"]["a_share_reentry_not_allowed"] is True
    assert report["safety"]["a_share_remains_blocked"] is True


def test_v2_11_g_validator_writes_reports_marker_and_hashes(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    _make_cache(cache_dir)
    source_c = tmp_path / "v2_11_c.json"
    source_f = tmp_path / "v2_11_f.json"
    marker_f = tmp_path / "v2_11_f.marker"
    _write_json(source_c, _source_c(cache_dir))
    _write_json(source_f, _source_f())
    marker_f.write_text("exit_code=0\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_11_g_test",
        command="test command",
        source_v2_11_c_report_json=source_c,
        source_v2_11_f_report_json=source_f,
        source_v2_11_f_pass_marker=marker_f,
        cache_dir=cache_dir,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["expanded_case_count_meets_retest_requirements"] is True
    assert report["hashes"]["expanded_cases_jsonl"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_11_g_cli_exits_zero_and_prints_no_secret_values(tmp_path: Path, capsys):
    cache_dir = tmp_path / "cache"
    _make_cache(cache_dir)
    source_c = tmp_path / "v2_11_c.json"
    source_f = tmp_path / "v2_11_f.json"
    marker_f = tmp_path / "v2_11_f.marker"
    _write_json(source_c, _source_c(cache_dir))
    _write_json(source_f, _source_f())
    marker_f.write_text("exit_code=0\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_11_g_cli",
            "--source-v2-11-c-report-json",
            str(source_c),
            "--source-v2-11-f-report-json",
            str(source_f),
            "--source-v2-11-f-pass-marker",
            str(marker_f),
            "--cache-dir",
            str(cache_dir),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

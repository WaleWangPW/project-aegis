from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.hypothesis_queue import build_strategy_sandbox_hypotheses
from aegis.strategy.research_source_catalog import canonical_strategy_research_records
from aegis.strategy.tushare_live_sandbox_refresh import (
    A_SHARE_SYMBOL_SEEDS,
    build_tushare_a_share_historical_cases,
    build_tushare_live_sandbox_refresh_report,
    is_tushare_a_core_ready,
)
import scripts.validate_v2_11_c_tushare_a_share_historical_sandbox_live_data_refresh as validator


def _probe() -> dict:
    return {
        "provider": "tushare",
        "token_present": True,
        "network_available": True,
        "summary": {"pass_count": 4, "unknown_count": 2},
        "checks": [
            {"market": "A", "data_type": "daily_bars", "status": "pass"},
            {"market": "A", "data_type": "index_bars", "status": "pass"},
            {"market": "A", "data_type": "stock_basic", "status": "pass"},
            {"market": "A", "data_type": "trading_calendar", "status": "pass"},
            {"market": "A", "data_type": "sector_classification", "status": "unknown_empty"},
            {"market": "A", "data_type": "fundamentals", "status": "unknown_empty"},
        ],
    }


def _manifest() -> dict:
    return {
        "project": "Project Aegis",
        "type": "p23_2_historical_market_cache_manifest",
        "generated_at": "2026-07-11T00:00:00+08:00",
        "start_date": "20240101",
        "end_date": "20240430",
        "daily_cache": {
            "directory": "data/cache/p23_2_historical_market/daily_by_trade_date",
            "expected_count": 90,
            "actual_count": 90,
            "failed_dates": [],
        },
        "dry_run": True,
        "sent": False,
        "trading_called": False,
        "overall_verdict": "PASS",
    }


def _hypotheses():
    return build_strategy_sandbox_hypotheses(
        canonical_strategy_research_records(),
        created_at="2026-07-11T00:00:00+08:00",
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_cache(cache_dir: Path) -> None:
    dates = [f"202401{day:02d}" for day in range(1, 91)]
    symbols = sorted({symbol for values in A_SHARE_SYMBOL_SEEDS.values() for symbol in values})
    _write_json(
        cache_dir / "trade_calendar.json",
        {
            "source": "Tushare trade_cal",
            "open_dates": dates,
            "rows": [{"cal_date": date, "is_open": 1} for date in dates],
        },
    )
    for day_index, date in enumerate(dates):
        rows = []
        for symbol_index, symbol in enumerate(symbols, start=1):
            base = 10.0 + symbol_index
            drift = 1.0 + (day_index * 0.001)
            close = round(base * drift, 4)
            rows.append(
                {
                    "ts_code": symbol,
                    "trade_date": date,
                    "open": close,
                    "high": round(close * 1.01, 4),
                    "low": round(close * 0.99, 4),
                    "close": close,
                    "vol": 100000.0 + symbol_index,
                    "amount": 1000000.0 + symbol_index,
                }
            )
        _write_json(
            cache_dir / "daily_by_trade_date" / f"{date}.json",
            {
                "source": "Tushare daily",
                "trade_date": date,
                "row_count": len(rows),
                "rows": rows,
            },
        )


def test_v2_11_c_probe_requires_tushare_a_core_capabilities():
    assert is_tushare_a_core_ready(_probe()) is True

    missing_daily = _probe()
    missing_daily["checks"] = [item for item in missing_daily["checks"] if item["data_type"] != "daily_bars"]

    assert is_tushare_a_core_ready(missing_daily) is False


def test_v2_11_c_builds_tushare_cache_historical_cases(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    _write_cache(cache_dir)

    cases = build_tushare_a_share_historical_cases(_hypotheses(), cache_dir=cache_dir)

    assert len(cases) == 8
    assert all(case.market == "A" for case in cases)
    assert all((case.evidence_ref or "").startswith("tushare_cache:") for case in cases)
    assert all(case.entry_price > 0 and case.exit_price > 0 for case in cases)


def test_v2_11_c_report_passes_refresh_chain_without_trade_mutation(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    _write_cache(cache_dir)

    report = build_tushare_live_sandbox_refresh_report(
        hypotheses=_hypotheses(),
        tushare_probe_report=_probe(),
        cache_manifest=_manifest(),
        cache_dir=cache_dir,
        run_id="v2_11_c_unit",
        command="unit test",
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["hypothesis_count"] == 2
    assert report["summary"]["historical_case_count"] == 8
    assert report["checks"]["tushare_a_core_ready"] is True
    assert report["checks"]["all_cases_have_tushare_cache_evidence"] is True
    assert report["safety"]["no_real_trade"] is True
    assert report["production_records_written"] is False


def test_v2_11_c_validator_writes_reports_marker_and_hashes(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    _write_cache(cache_dir)
    probe_json = tmp_path / "probe.json"
    manifest_json = tmp_path / "manifest.json"
    _write_json(probe_json, _probe())
    _write_json(manifest_json, _manifest())

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_11_c_test",
        command="test command",
        tushare_probe_report_json=probe_json,
        historical_cache_manifest_json=manifest_json,
        historical_cache_dir=cache_dir,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["cases_jsonl_written"] is True
    assert report["hashes"]["cases_jsonl"]
    assert report["safety"]["no_order_placement"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_11_c_cli_exits_zero_and_prints_no_token_value(tmp_path: Path, capsys):
    cache_dir = tmp_path / "cache"
    _write_cache(cache_dir)
    probe_json = tmp_path / "probe.json"
    manifest_json = tmp_path / "manifest.json"
    _write_json(probe_json, _probe())
    _write_json(manifest_json, _manifest())

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_11_c_cli",
            "--tushare-probe-report-json",
            str(probe_json),
            "--historical-cache-manifest-json",
            str(manifest_json),
            "--historical-cache-dir",
            str(cache_dir),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token=" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

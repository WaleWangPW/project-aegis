from __future__ import annotations

import csv
import json
from pathlib import Path

from aegis.strategy.refreshed_candidate_historical_sandbox import (
    build_refreshed_candidate_historical_sandbox_report,
    render_refreshed_candidate_historical_sandbox_markdown,
)
import scripts.validate_v2_14_c_refreshed_candidate_historical_sandbox as validator


def _refresh_report() -> dict:
    candidates = [
        ("600519.SH", "A", "strategy_a_low_vol_dividend_defensive"),
        ("600036.SH", "A", "strategy_a_low_vol_dividend_defensive"),
        ("601398.SH", "A", "strategy_a_low_vol_dividend_defensive"),
        ("00700.HK", "H", "strategy_h_low_vol_dividend"),
        ("00005.HK", "H", "strategy_h_low_vol_dividend"),
        ("00941.HK", "H", "strategy_h_low_vol_dividend"),
    ]
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.14-B Candidate Pool Live Refresh From Approved Routes",
        "run_id": "unit_v2_14_b",
        "summary": {
            "refreshed_candidate_count": 6,
            "refreshed_markets": ["A", "H"],
            "blocked_symbols_not_reused": ["CRCL", "MSFT", "NVDA"],
            "replacement_required_markets": ["US"],
        },
        "refreshed_candidates": [
            {
                "candidate_id": f"candidate_{symbol}",
                "symbol": symbol,
                "market": market,
                "strategy_id": strategy_id,
                "requires_historical_sandbox": True,
                "requires_suggestion_gate": True,
                "user_facing_suggestion_allowed": False,
            }
            for symbol, market, strategy_id in candidates
        ],
    }


def _case(symbol: str, entry: float, exit_: float, drawdown: float) -> dict:
    return {
        "case_id": f"a_{symbol}_case",
        "strategy_id": "strategy_a_low_vol_dividend_defensive",
        "date": "2026-01-01",
        "symbol": symbol,
        "market": "A",
        "entry_price": entry,
        "exit_price": exit_,
        "max_drawdown": drawdown,
        "risk_flags": [],
        "factor_values": {"actual_return": (exit_ - entry) / entry},
        "evidence_ref": f"tushare_cache:{symbol}:20260101:20260131",
    }


def _a_source_report() -> dict:
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.11-C Tushare A-Share Historical Sandbox Live Data Refresh",
        "historical_cases": [
            _case("600519.SH", 100.0, 101.0, -0.03),
            _case("600036.SH", 100.0, 98.0, -0.06),
        ],
    }


def _write_h_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerow({"date": "2026-07-01", "open": "100", "high": "101", "low": "99", "close": "100", "volume": "1"})
        writer.writerow({"date": "2026-07-08", "open": "101", "high": "103", "low": "100", "close": "102", "volume": "1"})


def _h_source_report(tmp_path: Path) -> dict:
    csv_path = tmp_path / "h_00700.csv"
    _write_h_csv(csv_path)
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-C H-US Historical Cache Readiness Dry Run",
        "results": [
            {
                "case_id": "h_00700_eodhd_daily_bars",
                "status": "pass",
                "market": "H",
                "canonical_symbol": "00700.HK",
                "normalized_csv": str(csv_path),
                "normalized_csv_sha256": "unit-hash",
            }
        ],
    }


def test_v2_14_c_evaluates_covered_candidates_and_exposes_missing_coverage(tmp_path: Path):
    report = build_refreshed_candidate_historical_sandbox_report(
        refresh_report=_refresh_report(),
        a_source_report=_a_source_report(),
        h_source_report=_h_source_report(tmp_path),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    covered_symbols = [item["symbol"] for item in report["covered_candidates"]]
    missing_symbols = [item["symbol"] for item in report["missing_coverage_candidates"]]

    assert report["overall_status"] == "PASS"
    assert set(covered_symbols) == {"600519.SH", "600036.SH", "00700.HK"}
    assert set(missing_symbols) == {"601398.SH", "00005.HK", "00941.HK"}
    assert report["summary"]["covered_candidate_count"] == 3
    assert report["summary"]["missing_coverage_count"] == 3
    assert report["summary"]["historical_case_count"] == 3
    assert report["checks"]["missing_coverage_visible"] is True
    assert report["checks"]["user_facing_suggestion_blocked"] is True


def test_v2_14_c_keeps_suggestion_gate_required_even_if_strategy_passes(tmp_path: Path):
    report = build_refreshed_candidate_historical_sandbox_report(
        refresh_report=_refresh_report(),
        a_source_report=_a_source_report(),
        h_source_report=_h_source_report(tmp_path),
        run_id="unit",
    )

    assert report["summary"]["strategy_pass_count"] >= 1
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    assert report["safety"]["suggestion_gate_required"] is True
    assert report["safety"]["not_user_facing_suggestion"] is True
    assert report["network_used"] is False


def test_v2_14_c_fails_if_blocked_symbol_is_reintroduced(tmp_path: Path):
    source = _refresh_report()
    source["refreshed_candidates"].append(
        {
            "candidate_id": "candidate_msft",
            "symbol": "MSFT",
            "market": "A",
            "strategy_id": "strategy_a_low_vol_dividend_defensive",
            "requires_historical_sandbox": True,
            "requires_suggestion_gate": True,
            "user_facing_suggestion_allowed": False,
        }
    )
    a_source = _a_source_report()
    a_source["historical_cases"].append(_case("MSFT", 100.0, 101.0, -0.01))

    report = build_refreshed_candidate_historical_sandbox_report(
        refresh_report=source,
        a_source_report=a_source,
        h_source_report=_h_source_report(tmp_path),
        run_id="unit",
    )

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["blocked_symbols_not_reused"] is False


def test_v2_14_c_markdown_is_not_a_suggestion(tmp_path: Path):
    report = build_refreshed_candidate_historical_sandbox_report(
        refresh_report=_refresh_report(),
        a_source_report=_a_source_report(),
        h_source_report=_h_source_report(tmp_path),
        run_id="unit",
    )
    md = render_refreshed_candidate_historical_sandbox_markdown(report)

    assert "Refreshed Candidate Historical Sandbox" in md
    assert "Missing Coverage" in md
    assert "Not a user-facing suggestion" in md
    assert "No real trade" in md
    assert "token=" not in md
    assert "https://" not in md


def test_v2_14_c_validator_writes_report_marker_and_cases(tmp_path: Path):
    refresh_path = tmp_path / "refresh.json"
    refresh_marker = tmp_path / "refresh.marker"
    a_path = tmp_path / "a.json"
    a_marker = tmp_path / "a.marker"
    h_path = tmp_path / "h.json"
    h_marker = tmp_path / "h.marker"
    refresh_path.write_text(json.dumps(_refresh_report(), ensure_ascii=False), encoding="utf-8")
    refresh_marker.write_text("source pass\n", encoding="utf-8")
    a_path.write_text(json.dumps(_a_source_report(), ensure_ascii=False), encoding="utf-8")
    a_marker.write_text("source pass\n", encoding="utf-8")
    h_path.write_text(json.dumps(_h_source_report(tmp_path), ensure_ascii=False), encoding="utf-8")
    h_marker.write_text("source pass\n", encoding="utf-8")
    record = tmp_path / "records" / "recommendations.jsonl"
    record.parent.mkdir()
    record.write_text("existing\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_14_c_test",
        command="test command",
        source_v2_14_b_report_json=refresh_path,
        source_v2_14_b_pass_marker=refresh_marker,
        source_v2_11_c_report_json=a_path,
        source_v2_11_c_pass_marker=a_marker,
        source_v2_12_c_report_json=h_path,
        source_v2_12_c_pass_marker=h_marker,
        record_paths={"recommendations_jsonl": record},
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["sandbox_json_written"] is True
    assert report["checks"]["cases_jsonl_written"] is True
    assert report["checks"]["production_record_files_unchanged"] is True
    assert record.read_text(encoding="utf-8") == "existing\n"
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_14_c_cli_like_acceptance_prints_no_secret_values(tmp_path: Path, capsys):
    refresh_path = tmp_path / "refresh.json"
    refresh_marker = tmp_path / "refresh.marker"
    a_path = tmp_path / "a.json"
    a_marker = tmp_path / "a.marker"
    h_path = tmp_path / "h.json"
    h_marker = tmp_path / "h.marker"
    refresh_path.write_text(json.dumps(_refresh_report(), ensure_ascii=False), encoding="utf-8")
    refresh_marker.write_text("source pass\n", encoding="utf-8")
    a_path.write_text(json.dumps(_a_source_report(), ensure_ascii=False), encoding="utf-8")
    a_marker.write_text("source pass\n", encoding="utf-8")
    h_path.write_text(json.dumps(_h_source_report(tmp_path), ensure_ascii=False), encoding="utf-8")
    h_marker.write_text("source pass\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_14_c_cli",
            "--source-v2-14-b-report-json",
            str(refresh_path),
            "--source-v2-14-b-pass-marker",
            str(refresh_marker),
            "--source-v2-11-c-report-json",
            str(a_path),
            "--source-v2-11-c-pass-marker",
            str(a_marker),
            "--source-v2-12-c-report-json",
            str(h_path),
            "--source-v2-12-c-pass-marker",
            str(h_marker),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "covered_candidate_count=3" in captured.out
    assert "missing_coverage_count=3" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

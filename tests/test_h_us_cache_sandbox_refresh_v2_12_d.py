from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.h_us_cache_sandbox_refresh import (
    build_h_us_cache_sandbox_refresh_report,
    historical_case_from_cache_result,
    render_h_us_cache_sandbox_refresh_markdown,
)
import scripts.validate_v2_12_d_h_us_historical_sandbox_candidate_refresh as validator


def _write_csv(path: Path, rows: list[tuple[str, float, float, float, float, int]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "date,open,high,low,close,volume\n"
        + "".join(f"{date},{open_},{high},{low},{close},{volume}\n" for date, open_, high, low, close, volume in rows),
        encoding="utf-8",
    )
    return str(path)


def _cache_readiness_report(tmp_path: Path) -> dict:
    h_csv = _write_csv(
        tmp_path / "cache" / "H" / "daily_bars" / "h.csv",
        [
            ("2026-07-01", 100, 102, 98, 100, 1000),
            ("2026-07-02", 100, 104, 99, 103, 1200),
        ],
    )
    us_csv = _write_csv(
        tmp_path / "cache" / "US" / "daily_bars" / "us.csv",
        [
            ("2026-07-01", 200, 202, 195, 200, 2000),
            ("2026-07-02", 200, 210, 198, 208, 2300),
        ],
    )
    return {
        "overall_status": "PASS",
        "acceptance_target": "V2.12-C H-US Historical Cache Readiness Dry Run",
        "run_id": "unit_v2_12_c",
        "summary": {"h_cache_ready": True, "us_cache_ready": True, "pass_count": 2},
        "results": [
            {
                "case_id": "h_00700_eodhd_daily_bars",
                "provider": "eodhd",
                "market": "H",
                "canonical_symbol": "00700.HK",
                "normalized_csv": h_csv,
                "normalized_csv_sha256": "hhash",
                "status": "pass",
            },
            {
                "case_id": "us_aapl_eodhd_daily_bars",
                "provider": "eodhd",
                "market": "US",
                "canonical_symbol": "AAPL.US",
                "normalized_csv": us_csv,
                "normalized_csv_sha256": "ushash",
                "status": "pass",
            },
        ],
    }


def test_v2_12_d_builds_cases_from_normalized_cache(tmp_path: Path):
    report = _cache_readiness_report(tmp_path)
    case = historical_case_from_cache_result(
        report["results"][0],
        strategy_id="strategy_h_cache_readiness_multifactor_probe",
    )

    assert case.market == "H"
    assert case.symbol == "00700.HK"
    assert case.entry_price == 100
    assert case.exit_price == 103
    assert case.evidence_ref.startswith("v2_12_c_normalized_cache:")


def test_v2_12_d_builds_preliminary_sandbox_report(tmp_path: Path):
    report = build_h_us_cache_sandbox_refresh_report(
        cache_readiness_report=_cache_readiness_report(tmp_path),
        run_id="unit",
        generated_at="2026-07-12T00:00:00+08:00",
    )
    text = json.dumps(report, ensure_ascii=False)

    assert report["overall_status"] == "PASS"
    assert report["network_used"] is False
    assert report["summary"]["candidate_count"] == 2
    assert report["summary"]["historical_case_count"] == 2
    assert report["summary"]["preliminary_only"] is True
    assert report["summary"]["user_facing_suggestion_allowed"] is False
    assert report["checks"]["suggestion_gate_required"] is True
    assert report["checks"]["production_records_not_mutated"] is True
    assert "api_token=" not in text
    assert "apikey=" not in text
    assert "https://" not in text


def test_v2_12_d_fails_if_source_not_v2_12_c(tmp_path: Path):
    source = _cache_readiness_report(tmp_path)
    source["overall_status"] = "FAIL"
    report = build_h_us_cache_sandbox_refresh_report(cache_readiness_report=source, run_id="unit")

    assert report["overall_status"] == "FAIL"
    assert report["checks"]["source_cache_readiness_pass"] is False


def test_v2_12_d_markdown_states_not_user_suggestion(tmp_path: Path):
    report = build_h_us_cache_sandbox_refresh_report(
        cache_readiness_report=_cache_readiness_report(tmp_path),
        run_id="unit",
    )
    md = render_h_us_cache_sandbox_refresh_markdown(report)

    assert "Preliminary historical sandbox input only" in md
    assert "cannot prove a production strategy" in md
    assert "No user-facing suggestion is allowed" in md
    assert "No real trade" in md


def test_v2_12_d_validator_writes_report_and_marker(tmp_path: Path):
    source = tmp_path / "cache_readiness.json"
    source.write_text(json.dumps(_cache_readiness_report(tmp_path), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_12_d_test",
        command="test command",
        source_cache_readiness_report_json=source,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["sandbox_report_json_written"] is True
    assert report["checks"]["cases_jsonl_written"] is True
    assert report["safety"]["no_broker_api"] is True
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_12_d_cli_exits_zero(tmp_path: Path, capsys):
    source = tmp_path / "cache_readiness.json"
    source.write_text(json.dumps(_cache_readiness_report(tmp_path), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_12_d_cli",
            "--source-cache-readiness-report-json",
            str(source),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

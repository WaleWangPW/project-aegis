from __future__ import annotations

import json
from pathlib import Path

import scripts.build_a_share_tushare_source_feature_coverage as coverage


def _queue() -> dict:
    return {
        "hypothesis_count": 2,
        "hypotheses": [
            {"hypothesis_id": "hyp_a_tushare_capital_flow_accumulation", "title": "Capital flow"},
            {"hypothesis_id": "hyp_a_tushare_factor_liquidity_quality_overlay", "title": "Factor overlay"},
        ],
    }


def _cases_report() -> dict:
    cases = [
        {"case_id": "case_1", "symbol": "603893", "ts_code": "603893.SH", "market": "A", "entry_date": "2024-01-02"},
        {"case_id": "case_2", "symbol": "300059", "ts_code": "300059.SZ", "market": "A", "entry_date": "2024-01-03"},
        {"case_id": "case_us", "symbol": "VRTX", "market": "US", "entry_date": "2024-01-02"},
    ]
    return {"status": "PASS", "summary": {"a_share_case_count": 2}, "historical_cases": cases}


def _evaluation() -> dict:
    return {
        "items": [
            {"hypothesis_id": "hyp_a_tushare_capital_flow_accumulation", "eligible_symbols": ["603893", "300059"]},
            {"hypothesis_id": "hyp_a_tushare_factor_liquidity_quality_overlay", "eligible_symbols": ["603893", "300059"]},
        ]
    }


def _observations() -> list[dict]:
    rows = []
    for case_id in ("case_1", "case_2"):
        rows.append({"case_id": case_id, "endpoint": "moneyflow", "status": "PASS"})
        rows.append({"case_id": case_id, "endpoint": "stk_factor", "status": "PASS"})
        rows.append({"case_id": case_id, "endpoint": "daily_basic", "status": "MISSING_FOR_CASE" if case_id == "case_2" else "PASS"})
    return rows


def test_feature_coverage_report_marks_ready_and_gaps_without_suggestions():
    report = coverage.build_feature_coverage_report(
        _queue(),
        _cases_report(),
        _evaluation(),
        _observations(),
        run_id="unit",
        network_used=False,
        command="unit",
    )

    assert report["status"] == "PASS"
    assert report["summary"]["hypothesis_count"] == 2
    assert report["summary"]["ready_for_deep_sandbox_count"] == 2
    assert report["items"][0]["feature_status"] == "READY_FOR_DEEP_SANDBOX"
    assert report["items"][1]["min_endpoint_coverage"] == 0.5
    assert report["safety"]["raw_payload_saved"] is False
    assert report["safety"]["requires_deep_source_specific_sandbox_before_ranking"] is True
    assert all(item["user_facing_suggestion_allowed"] is False for item in report["items"])


class _UnconfiguredAdapter:
    def is_configured(self) -> bool:
        return False


def test_feature_coverage_cli_writes_blocked_report_without_secret(tmp_path: Path, capsys, monkeypatch):
    queue_json = tmp_path / "queue.json"
    cases_json = tmp_path / "cases.json"
    evaluation_json = tmp_path / "evaluation.json"
    queue_json.write_text(json.dumps(_queue(), ensure_ascii=False), encoding="utf-8")
    cases_json.write_text(json.dumps(_cases_report(), ensure_ascii=False), encoding="utf-8")
    evaluation_json.write_text(json.dumps(_evaluation(), ensure_ascii=False), encoding="utf-8")

    old_reports = coverage.REPORTS
    old_processed = coverage.PROCESSED
    old_out_json = coverage.OUT_JSON
    old_out_md = coverage.OUT_MD
    old_pass = coverage.PASS_MARKER
    old_blocked = coverage.BLOCKED_MARKER
    try:
        monkeypatch.setattr(coverage.TushareAdapter, "from_env", lambda: _UnconfiguredAdapter())
        coverage.REPORTS = tmp_path / "reports"
        coverage.PROCESSED = tmp_path / "processed"
        coverage.OUT_JSON = coverage.REPORTS / "a_share_tushare_source_feature_coverage_latest.json"
        coverage.OUT_MD = coverage.REPORTS / "a_share_tushare_source_feature_coverage_latest.md"
        coverage.PASS_MARKER = coverage.REPORTS / "A_SHARE_TUSHARE_SOURCE_FEATURE_COVERAGE_PASS.marker"
        coverage.BLOCKED_MARKER = coverage.REPORTS / "A_SHARE_TUSHARE_SOURCE_FEATURE_COVERAGE_BLOCKED.marker"
        exit_code = coverage.main(
            [
                "--queue-json",
                str(queue_json),
                "--cases-json",
                str(cases_json),
                "--evaluation-json",
                str(evaluation_json),
                "--run-id",
                "unit",
            ]
        )
        captured = capsys.readouterr()
    finally:
        coverage.REPORTS = old_reports
        coverage.PROCESSED = old_processed
        coverage.OUT_JSON = old_out_json
        coverage.OUT_MD = old_out_md
        coverage.PASS_MARKER = old_pass
        coverage.BLOCKED_MARKER = old_blocked

    assert exit_code == 2
    assert "BLOCKED_MISSING_TUSHARE_TOKEN" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token=" not in captured.out.lower()
    assert (tmp_path / "reports" / "A_SHARE_TUSHARE_SOURCE_FEATURE_COVERAGE_BLOCKED.marker").exists()

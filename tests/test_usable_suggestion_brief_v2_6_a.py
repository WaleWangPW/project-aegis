from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_6_a_usable_suggestion_brief as validator
from aegis.strategy.suggestion_brief import build_usable_suggestion_brief, render_usable_suggestion_brief_markdown


def _bindings() -> list[dict]:
    return [
        {
            "suggestion_id": "sug_a",
            "strategy_id": "strategy_a",
            "market": "A",
            "binding_status": "bound",
            "bound_candidates": [
                {"symbol": "600036.SH", "market": "A", "name": "招商银行", "source": "api_fixture", "score": 0.86, "status": "Watch"}
            ],
            "blocked_by": [],
            "evidence_refs": ["v2_5_c_report.json"],
            "warnings": ["Simulation-only refreshed candidate binding."],
        },
        {
            "suggestion_id": "sug_h",
            "strategy_id": "strategy_h",
            "market": "H",
            "binding_status": "bound",
            "bound_candidates": [
                {"symbol": "00700.HK", "market": "H", "name": "Tencent Holdings", "source": "api_fixture", "score": 0.82, "status": "Watch"}
            ],
            "blocked_by": [],
            "evidence_refs": ["v2_5_c_report.json"],
            "warnings": ["Simulation-only refreshed candidate binding."],
        },
        {
            "suggestion_id": "sug_us",
            "strategy_id": "strategy_us",
            "market": "US",
            "binding_status": "bound",
            "bound_candidates": [
                {"symbol": "MSFT", "market": "US", "name": "Microsoft", "source": "api_fixture", "score": 0.79, "status": "Watch"}
            ],
            "blocked_by": [],
            "evidence_refs": ["v2_5_c_report.json"],
            "warnings": ["Simulation-only refreshed candidate binding."],
        },
        {
            "suggestion_id": "sug_blocked",
            "strategy_id": "strategy_blocked",
            "market": "US",
            "binding_status": "blocked",
            "bound_candidates": [],
            "blocked_by": ["strategy_sandbox_not_passed"],
            "evidence_refs": ["v2_5_c_report.json"],
            "warnings": ["Blocked strategy path."],
        },
    ]


def _drafts() -> list[dict]:
    return [
        {"suggestion_id": "sug_a", "symbol": "A_BASKET", "market": "A", "reasons": ["sandbox_status=PASS"], "risk_warnings": ["liquidity_filter"], "evidence_refs": ["v2_4_d.json"]},
        {"suggestion_id": "sug_h", "symbol": "H_BASKET", "market": "H", "reasons": ["sandbox_status=PASS"], "risk_warnings": ["stock_connect_context"], "evidence_refs": ["v2_4_d.json"]},
        {"suggestion_id": "sug_us", "symbol": "US_BASKET", "market": "US", "reasons": ["sandbox_status=PASS"], "risk_warnings": ["valuation_check"], "evidence_refs": ["v2_4_d.json"]},
        {"suggestion_id": "sug_blocked", "symbol": "US_BLOCKED", "market": "US", "reasons": ["sandbox_status=FAIL"], "risk_warnings": ["drawdown"], "evidence_refs": ["v2_4_d.json"]},
    ]


def test_usable_suggestion_brief_has_candidates_and_blocked_paths():
    report = build_usable_suggestion_brief(
        bindings=_bindings(),
        suggestion_drafts=_drafts(),
        run_id="v2_6_a_unit",
        evidence_refs=["v2_5_c_marker"],
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["candidate_markets"] == ["A", "H", "US"]
    assert report["summary"]["candidate_symbols"] == ["600036.SH", "00700.HK", "MSFT"]
    assert report["summary"]["blocked_count"] == 1
    assert report["checks"]["no_live_price_or_position_size"] is True
    assert report["safety"]["no_real_trade"] is True
    assert all(item["suggested_user_action"] != "place_order" for item in report["items"])

    md = render_usable_suggestion_brief_markdown(report)
    assert "Usable Suggestion Brief" in md
    assert "不接 Broker API" in md


def test_v2_6_a_acceptance_writes_reports_and_hashes(tmp_path: Path):
    bindings_json = tmp_path / "bindings.json"
    drafts_json = tmp_path / "drafts.json"
    bindings_json.write_text(json.dumps(_bindings(), ensure_ascii=False), encoding="utf-8")
    drafts_json.write_text(json.dumps(_drafts(), ensure_ascii=False), encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        run_id="v2_6_a_test",
        command="test command",
        bindings_json=bindings_json,
        suggestion_drafts_json=drafts_json,
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["has_a_h_us_candidates"] is True
    assert report["checks"]["blocked_paths_visible"] is True
    assert report["checks"]["no_real_trade_or_broker"] is True
    assert report["hashes"]["brief_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_6_a_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    bindings_json = tmp_path / "bindings.json"
    drafts_json = tmp_path / "drafts.json"
    bindings_json.write_text(json.dumps(_bindings(), ensure_ascii=False), encoding="utf-8")
    drafts_json.write_text(json.dumps(_drafts(), ensure_ascii=False), encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "v2_6_a_cli",
            "--bindings-json",
            str(bindings_json),
            "--suggestion-drafts-json",
            str(drafts_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "token" not in captured.out.lower()
    assert "secret" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

from __future__ import annotations

import json
from pathlib import Path

import scripts.validate_v2_8_f_refresh_queue_usable_brief as validator
from aegis.strategy.refresh_queue_brief import (
    build_refresh_queue_usable_brief,
    render_refresh_queue_usable_brief_markdown,
)


def _drafts() -> list[dict]:
    return [
        {
            "suggestion_id": "sug_a_allowed",
            "strategy_id": "strategy_a",
            "action": "paper_entry_candidate",
            "symbol": "A_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "A",
            "reasons": ["sandbox_status=PASS", "win_rate=0.7500"],
            "risk_warnings": ["No live price, order size, or broker execution is produced."],
            "blocked_by": [],
            "evidence_refs": ["v2_8_e_report.json"],
            "simulation_only": True,
            "user_must_execute_externally": True,
        },
        {
            "suggestion_id": "sug_h_allowed",
            "strategy_id": "strategy_h",
            "action": "paper_entry_candidate",
            "symbol": "H_LOW_VOL_DIVIDEND_PAPER_BASKET",
            "market": "H",
            "reasons": ["sandbox_status=PASS", "win_rate=0.7500"],
            "risk_warnings": ["No live price, order size, or broker execution is produced."],
            "blocked_by": [],
            "evidence_refs": ["v2_8_e_report.json"],
            "simulation_only": True,
            "user_must_execute_externally": True,
        },
        {
            "suggestion_id": "sug_us_allowed",
            "strategy_id": "strategy_us",
            "action": "paper_entry_candidate",
            "symbol": "US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET",
            "market": "US",
            "reasons": ["sandbox_status=PASS", "win_rate=0.7500"],
            "risk_warnings": ["No live price, order size, or broker execution is produced."],
            "blocked_by": [],
            "evidence_refs": ["v2_8_e_report.json"],
            "simulation_only": True,
            "user_must_execute_externally": True,
        },
        {
            "suggestion_id": "sug_us_blocked",
            "strategy_id": "strategy_us_blocked",
            "action": "blocked",
            "symbol": "US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET",
            "market": "US",
            "reasons": ["sandbox_status=FAIL"],
            "risk_warnings": ["drawdown"],
            "blocked_by": ["strategy_sandbox_not_passed"],
            "evidence_refs": ["v2_8_e_report.json"],
            "simulation_only": True,
            "user_must_execute_externally": True,
        },
    ]


def test_refresh_queue_usable_brief_has_candidate_baskets_and_blocked_paths():
    report = build_refresh_queue_usable_brief(
        suggestion_drafts=_drafts(),
        run_id="v2_8_f_unit",
        evidence_refs=["v2_8_e_marker"],
        generated_at="2026-07-11T00:00:00+08:00",
    )

    assert report["overall_status"] == "PASS"
    assert report["summary"]["candidate_markets"] == ["A", "H", "US"]
    assert report["summary"]["candidate_count"] == 3
    assert report["summary"]["blocked_count"] == 1
    assert report["checks"]["blocked_paths_visible"] is True
    assert report["checks"]["no_live_price"] is True
    assert report["checks"]["no_position_size"] is True
    assert report["safety"]["strategy_basket_not_stock_order"] is True
    assert all(item["suggested_user_action"] != "place_order" for item in report["items"])

    md = render_refresh_queue_usable_brief_markdown(report)
    assert "Refresh Queue Usable Brief" in md
    assert "不是具体个股买卖建议" in md


def test_v2_8_f_acceptance_writes_reports_and_hashes(tmp_path: Path):
    drafts_json = tmp_path / "drafts.json"
    drafts_json.write_text(json.dumps(_drafts(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = validator.run_acceptance(
        output_root=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
        suggestion_drafts_json=drafts_json,
        run_id="v2_8_f_test",
        command="test command",
    )

    assert report["overall_status"] == "PASS"
    assert report["checks"]["has_a_h_us_candidate_baskets"] is True
    assert report["checks"]["blocked_paths_visible"] is True
    assert report["checks"]["strategy_basket_not_stock_order"] is True
    assert report["checks"]["no_real_trade"] is True
    assert report["production_records_written"] is False
    assert report["dashboard_contract_changed"] is False
    assert report["hashes"]["brief_json"]
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()


def test_v2_8_f_cli_exits_zero_and_prints_no_secrets(tmp_path: Path, capsys):
    drafts_json = tmp_path / "drafts.json"
    drafts_json.write_text(json.dumps(_drafts(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    exit_code = validator.main(
        [
            "--output-root",
            str(tmp_path / "processed"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--suggestion-drafts-json",
            str(drafts_json),
            "--run-id",
            "v2_8_f_cli",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / validator.PASS_MARKER).exists()

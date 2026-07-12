from __future__ import annotations

import json
from pathlib import Path

from aegis.strategy.a_share_tushare_source_hypotheses import build_a_share_tushare_source_hypothesis_queue
import scripts.build_a_share_tushare_source_hypothesis_queue as builder


def _probe() -> dict:
    modules = [
        ("capital_flow", "主力资金流向", "moneyflow", "PASS"),
        ("dragon_tiger_hot_money", "龙虎榜 / 游资席位", "top_list", "PASS"),
        ("dragon_tiger_hot_money", "龙虎榜 / 游资席位", "top_inst", "PASS"),
        ("institutional_ownership", "机构持仓与股东变化", "top10_holders", "PASS"),
        ("institutional_ownership", "机构持仓与股东变化", "top10_floatholders", "PASS"),
        ("holder_concentration", "股东人数 / 筹码集中", "stk_holdernumber", "PASS"),
        ("factor_base", "A 股因子与日线基础池", "stk_factor", "PASS"),
        ("factor_base", "A 股因子与日线基础池", "daily_basic", "PASS"),
        ("governance", "高管薪酬 / 治理", "stk_rewards", "PASS"),
        ("institutional_research", "机构调研热度", "stk_survey", "ERROR"),
    ]
    return {
        "overall_status": "PASS",
        "generated_at": "2026-07-12T19:00:00+08:00",
        "provider": "tushare",
        "market": "A",
        "latest_trade_date": "20260710",
        "modules": [
            {
                "module_id": module_id,
                "module_name": module_name,
                "endpoint": endpoint,
                "status": status,
                "row_count": 10 if status == "PASS" else 0,
                "error_message": "permission or endpoint unavailable" if status != "PASS" else None,
            }
            for module_id, module_name, endpoint, status in modules
        ],
    }


def test_builds_a_share_source_hypotheses_without_direct_suggestions():
    queue = build_a_share_tushare_source_hypothesis_queue(_probe(), created_at="2026-07-12T19:00:00+08:00")

    assert queue["hypothesis_count"] == 6
    assert queue["market_coverage"]["A"] == 6
    assert queue["strategy_family_coverage"]["capital_flow"] == 1
    assert queue["strategy_family_coverage"]["hot_money"] == 1
    assert queue["strategy_family_coverage"]["institutional_ownership"] == 1
    assert queue["strategy_family_coverage"]["holder_concentration"] == 1
    assert queue["safety"]["requires_sandbox"] is True
    assert queue["safety"]["auto_applied"] is False
    assert queue["safety"]["user_facing_suggestion_allowed"] is False
    assert queue["safety"]["no_order_placement"] is True
    assert len(queue["hypothesis_hashes"]) == 6
    assert any(item["endpoint"] == "stk_survey" for item in queue["blocked_or_skipped_sources"])


def test_builder_writes_reports_marker_and_prints_no_secret(tmp_path: Path, capsys):
    probe_json = tmp_path / "probe.json"
    probe_json.write_text(json.dumps(_probe(), ensure_ascii=False), encoding="utf-8")

    old_reports = builder.REPORTS
    old_processed = builder.PROCESSED
    old_latest_json = builder.LATEST_JSON
    old_latest_md = builder.LATEST_MD
    old_pass_marker = builder.PASS_MARKER
    old_blocked_marker = builder.BLOCKED_MARKER
    try:
        builder.REPORTS = tmp_path / "reports"
        builder.PROCESSED = tmp_path / "processed"
        builder.LATEST_JSON = builder.REPORTS / "a_share_tushare_source_hypothesis_queue_latest.json"
        builder.LATEST_MD = builder.REPORTS / "a_share_tushare_source_hypothesis_queue_latest.md"
        builder.PASS_MARKER = builder.REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_QUEUE_PASS.marker"
        builder.BLOCKED_MARKER = builder.REPORTS / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_QUEUE_BLOCKED.marker"

        exit_code = builder.main(["--source-probe", str(probe_json), "--run-id", "unit"])
        captured = capsys.readouterr()
    finally:
        builder.REPORTS = old_reports
        builder.PROCESSED = old_processed
        builder.LATEST_JSON = old_latest_json
        builder.LATEST_MD = old_latest_md
        builder.PASS_MARKER = old_pass_marker
        builder.BLOCKED_MARKER = old_blocked_marker

    assert exit_code == 0
    assert "PASS" in captured.out
    assert "secret" not in captured.out.lower()
    assert "token" not in captured.out.lower()
    assert (tmp_path / "reports" / "A_SHARE_TUSHARE_SOURCE_HYPOTHESIS_QUEUE_PASS.marker").exists()

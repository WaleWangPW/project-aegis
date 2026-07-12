from __future__ import annotations

import scripts.build_aegis_strategy_specific_historical_cases as cases


def test_a_share_research_samples_are_labelled_and_not_suggestions():
    base = [{"symbol": "603893", "market": "A", "matched_strategy_ids": ["qvm"]}]
    workbench = {
        "candidates": [
            {
                "symbol": "603893",
                "market": "A",
                "status": "high_risk_watch",
                "name": "duplicate",
            },
            {
                "symbol": "300475",
                "market": "A",
                "status": "high_risk_watch",
                "name": "香农芯创",
                "score": 41,
                "strategy_matches": ["毛利率连升3季", "新增机构调研", "ROE连升3季"],
                "risk_flags": ["一年涨幅超过300%，过热降权"],
            },
            {
                "symbol": "002709",
                "market": "A",
                "status": "blocked",
                "name": "天赐材料",
                "strategy_matches": ["主业贡献高"],
                "risk_flags": ["现金流为负", "趋势向下"],
            },
            {
                "symbol": "PANW",
                "market": "US",
                "status": "high_risk_watch",
                "name": "Palo Alto Networks",
            },
        ]
    }

    samples, summary = cases.a_share_research_samples(
        workbench,
        base,
        {"300475": "300475.SZ", "002709": "002709.SZ"},
    )

    assert summary["added_candidate_count"] == 2
    assert summary["added_symbols"] == ["300475", "002709"]
    assert all(item["research_sample_only"] is True for item in samples)
    assert all(item["sample_source"] == "stock_selection_workbench" for item in samples)
    assert all(item["user_facing_suggestion_allowed"] is False for item in samples)
    assert all(item["real_trade_allowed"] is False for item in samples)
    assert "qvm" in samples[0]["matched_strategy_ids"]
    assert "growth_breakout" in samples[0]["matched_strategy_ids"]
    assert "low_vol_momentum" in samples[1]["matched_strategy_ids"]


def test_a_share_research_sample_cases_carry_safety_metadata():
    item = {
        "symbol": "300475",
        "name": "香农芯创",
        "market": "A",
        "matched_strategy_ids": ["qvm", "a_share_short_momentum"],
        "research_sample_only": True,
        "sample_source": "stock_selection_workbench",
        "source_status": "high_risk_watch",
    }
    dates = [f"202401{day:02d}" for day in range(1, 31)]
    rows_by_date = {
        date: {"300475.SZ": {"close": 100 + index}}
        for index, date in enumerate(dates)
    }
    source_hashes = {date: f"hash-{date}" for date in dates}

    assembled, result = cases.build_cases_for_candidate(
        item,
        "300475.SZ",
        dates,
        rows_by_date,
        source_hashes,
    )

    assert result["status"] == "case_assembled"
    assert assembled
    assert all(case["research_sample_only"] is True for case in assembled)
    assert all(case["sample_source"] == "stock_selection_workbench" for case in assembled)
    assert all(case["future_data_used_for_selection"] is False for case in assembled)

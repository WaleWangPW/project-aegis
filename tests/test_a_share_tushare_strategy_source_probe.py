from __future__ import annotations

import pandas as pd

import scripts.probe_a_share_tushare_strategy_sources as probe


class _Spec:
    module_id = "capital_flow"
    endpoint = "moneyflow"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def call(self, _pro, trade_date: str, _start: str, _end: str):
        self.calls.append(trade_date)
        if trade_date == "20240703":
            return pd.DataFrame([{"ts_code": "600000.SH", "net_mf_amount": 100.0}])
        return pd.DataFrame()


def test_historical_scan_endpoint_finds_first_non_empty_date():
    spec = _Spec()

    result = probe.historical_scan_endpoint(
        object(),
        spec,  # type: ignore[arg-type]
        ["20240704", "20240703", "20240702"],
        "20240101",
        "20240710",
    )

    assert result["matched"] is True
    assert result["trade_date"] == "20240703"
    assert result["row_count"] == 1
    assert result["checked_count"] == 2
    assert probe.historical_scan_modules("daily_core") == {"capital_flow", "factor_base"}

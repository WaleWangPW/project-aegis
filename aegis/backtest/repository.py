"""BacktestRepository — Phase 7 §5.3 (optional output helper).

Writes backtest artifacts under an isolated `data/processed/backtests/
<run_id>/` directory — never `data/records/`. Uses the same JSONL
conventions as every other repository in this project
(`aegis/utils/jsonl.py`), plus plain JSON for the single `MetricsReport`
and a markdown rendering for humans.
"""

from __future__ import annotations

import json
from pathlib import Path

from aegis.backtest.models import BacktestResult, MetricsReport
from aegis.utils.jsonl import append_jsonl, read_jsonl

BACKTEST_RESULTS_FILENAME = "backtest_results.jsonl"
METRICS_REPORT_JSON_FILENAME = "metrics_report.json"
METRICS_REPORT_MD_FILENAME = "metrics_report.md"
DATA_ACCESS_LOG_FILENAME = "data_access_log.jsonl"


class BacktestRepository:
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)

    def append_result(self, result: BacktestResult) -> None:
        append_jsonl(self.output_dir / BACKTEST_RESULTS_FILENAME, result.model_dump())

    def list_results(self) -> list[BacktestResult]:
        return [BacktestResult(**row) for row in read_jsonl(self.output_dir / BACKTEST_RESULTS_FILENAME)]

    def write_metrics_report(self, report: MetricsReport, markdown: str) -> tuple[Path, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.output_dir / METRICS_REPORT_JSON_FILENAME
        json_path.write_text(json.dumps(report.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        md_path = self.output_dir / METRICS_REPORT_MD_FILENAME
        md_path.write_text(markdown, encoding="utf-8")
        return json_path, md_path

    def append_access_log_entries(self, entries: list[dict]) -> None:
        for entry in entries:
            append_jsonl(self.output_dir / DATA_ACCESS_LOG_FILENAME, entry)

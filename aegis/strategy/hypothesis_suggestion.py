"""Convert sandboxed research hypotheses into gated suggestion drafts.

This module is an adapter between V2.4-C historical sandbox evidence and the
existing Suggestion Gate. It never writes production recommendation records and
never turns a sandbox PASS into a real trade instruction.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from aegis.models.strategy_hypothesis import StrategySandboxHypothesis
from aegis.models.suggestion import SuggestionOpportunity
from aegis.strategy.suggestion_gate import build_suggestion_gate_report

_PAPER_SYMBOL_BY_HYPOTHESIS = {
    "hyp_a_low_vol_dividend_defensive": "A_LOW_VOL_DIVIDEND_PAPER_BASKET",
    "hyp_a_value_quality_multifactor": "A_VALUE_QUALITY_PAPER_BASKET",
    "hyp_h_smart_beta_multifactor": "H_SMART_BETA_PAPER_BASKET",
    "hyp_h_low_vol_dividend": "H_LOW_VOL_DIVIDEND_PAPER_BASKET",
    "hyp_us_value_quality_momentum": "US_VALUE_QUALITY_MOMENTUM_PAPER_BASKET",
    "hyp_us_low_vol_risk_overlay": "US_LOW_VOL_RISK_OVERLAY_PAPER_BASKET",
}


def _hypothesis_by_id(hypotheses: Sequence[StrategySandboxHypothesis]) -> dict[str, StrategySandboxHypothesis]:
    return {hypothesis.hypothesis_id: hypothesis for hypothesis in hypotheses}


def _result_by_strategy(sandbox_report: Mapping) -> dict[str, Mapping]:
    return {result["strategy_id"]: result for result in sandbox_report.get("results", [])}


def _format_metric(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _opportunity_for_result(
    *,
    strategy_id: str,
    hypothesis: StrategySandboxHypothesis,
    result: Mapping,
    evidence_refs: Sequence[str],
) -> SuggestionOpportunity:
    metrics = result.get("metrics", {})
    failed_reasons = metrics.get("failed_reasons", [])
    status = result.get("status")
    metric_reasons = [
        f"sandbox_status={status}",
        f"win_rate={_format_metric(metrics.get('win_rate'))}",
        f"average_return={_format_metric(metrics.get('average_return'))}",
        f"max_drawdown={_format_metric(metrics.get('max_drawdown'))}",
    ]
    if failed_reasons:
        metric_reasons.append("failed_reasons=" + ",".join(failed_reasons))

    risk_warnings = [
        "Research-hypothesis draft only; not a production recommendation.",
        "No live price, order size, or broker execution is produced.",
    ]
    risk_warnings.extend(hypothesis.proposed_risk_controls[:3])

    return SuggestionOpportunity(
        opportunity_id=f"research_{hypothesis.hypothesis_id}",
        strategy_id=strategy_id,
        symbol=_PAPER_SYMBOL_BY_HYPOTHESIS.get(hypothesis.hypothesis_id, f"{hypothesis.market}_PAPER_BASKET"),
        market=hypothesis.market,
        name=hypothesis.title,
        risk_veto=False,
        evidence_refs=list(evidence_refs),
        reasons=[hypothesis.thesis, *metric_reasons],
        risk_warnings=risk_warnings,
    )


def build_hypothesis_suggestion_opportunities(
    hypotheses: Sequence[StrategySandboxHypothesis],
    sandbox_report: Mapping,
    *,
    evidence_refs: Sequence[str],
) -> list[SuggestionOpportunity]:
    """Build one gated opportunity per sandboxed hypothesis result."""

    hypotheses_by_id = _hypothesis_by_id(hypotheses)
    strategy_to_hypothesis = sandbox_report.get("strategy_to_hypothesis", {})
    results_by_strategy = _result_by_strategy(sandbox_report)
    opportunities: list[SuggestionOpportunity] = []

    for strategy_id in sorted(results_by_strategy):
        hypothesis_id = strategy_to_hypothesis.get(strategy_id)
        if not hypothesis_id:
            continue
        hypothesis = hypotheses_by_id[hypothesis_id]
        opportunities.append(
            _opportunity_for_result(
                strategy_id=strategy_id,
                hypothesis=hypothesis,
                result=results_by_strategy[strategy_id],
                evidence_refs=evidence_refs,
            )
        )
    return opportunities


def build_hypothesis_suggestion_gate_report(
    hypotheses: Sequence[StrategySandboxHypothesis],
    sandbox_report: Mapping,
    *,
    run_id: str,
    evidence_refs: Sequence[str],
    command: str | None = None,
) -> dict:
    """Route sandboxed hypotheses through the existing Suggestion Gate."""

    opportunities = build_hypothesis_suggestion_opportunities(
        hypotheses,
        sandbox_report,
        evidence_refs=evidence_refs,
    )
    report = build_suggestion_gate_report(
        opportunities,
        sandbox_report,
        run_id=run_id,
        command=command,
    )
    summary = sandbox_report.get("summary", {})
    report["acceptance_target"] = "V2.4-D Research Hypotheses To Suggestion Gate Drafts"
    report["source_acceptance_target"] = sandbox_report.get("acceptance_target")
    report["source_hypothesis_count"] = summary.get("hypothesis_count", len(hypotheses))
    report["source_passing_hypotheses"] = summary.get("passing_hypotheses", [])
    report["source_failing_hypotheses"] = summary.get("failing_hypotheses", [])
    report["safety"]["research_hypothesis_source_only"] = True
    report["safety"]["no_live_price_or_position_size"] = True
    report["safety"]["suggestion_drafts_not_orders"] = True
    return report


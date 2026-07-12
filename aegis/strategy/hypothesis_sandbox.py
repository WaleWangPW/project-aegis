"""Evaluate research hypotheses through the existing historical sandbox."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from aegis.models.strategy import HistoricalStrategyCase, StrategyCandidate, StrategyPassCriteria
from aegis.models.strategy_hypothesis import StrategySandboxHypothesis
from aegis.strategy.sandbox import build_strategy_sandbox_report


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _candidate_id(hypothesis_id: str) -> str:
    return hypothesis_id.replace("hyp_", "strategy_", 1)


def _factor_family(hypothesis: StrategySandboxHypothesis) -> str:
    families = set(hypothesis.strategy_families)
    if "multi_factor" in families:
        return "multi_factor"
    if "risk_overlay" in families:
        return "risk_overlay"
    return hypothesis.strategy_families[0]


def _pass_criteria(hypothesis: StrategySandboxHypothesis) -> StrategyPassCriteria:
    if hypothesis.market == "A":
        return StrategyPassCriteria(
            min_sample_count=4,
            min_win_rate=0.5,
            min_average_return=0.008,
            max_drawdown_floor=-0.08,
        )
    if hypothesis.market == "H":
        return StrategyPassCriteria(
            min_sample_count=4,
            min_win_rate=0.5,
            min_average_return=0.006,
            max_drawdown_floor=-0.09,
        )
    return StrategyPassCriteria(
        min_sample_count=4,
        min_win_rate=0.55,
        min_average_return=0.01,
        max_drawdown_floor=-0.1,
    )


def strategy_candidate_from_hypothesis(
    hypothesis: StrategySandboxHypothesis,
    *,
    created_at: str | None = None,
) -> StrategyCandidate:
    created = created_at or _now_iso()
    return StrategyCandidate(
        strategy_id=_candidate_id(hypothesis.hypothesis_id),
        name=hypothesis.title.replace(" hypothesis", " sandbox candidate"),
        market=hypothesis.market,
        universe=hypothesis.proposed_universe,
        factor_family=_factor_family(hypothesis),
        entry_rule="; ".join(hypothesis.proposed_entry_logic),
        exit_rule="; ".join(hypothesis.proposed_exit_logic),
        exit_horizon_days=20,
        risk_controls=hypothesis.proposed_risk_controls,
        pass_criteria=_pass_criteria(hypothesis),
        source_research_refs=hypothesis.source_research_ids,
        created_at=created,
    )


def strategy_candidates_from_hypotheses(
    hypotheses: Iterable[StrategySandboxHypothesis],
    *,
    created_at: str | None = None,
) -> list[StrategyCandidate]:
    return [strategy_candidate_from_hypothesis(hypothesis, created_at=created_at) for hypothesis in hypotheses]


def fixture_historical_cases_for_hypotheses(hypotheses: Iterable[StrategySandboxHypothesis]) -> list[HistoricalStrategyCase]:
    """Return deterministic historical cases for isolated acceptance evaluation.

    These cases are acceptance fixtures. They prove the hypothesis queue can
    flow through the sandbox gate with explicit PASS/FAIL evidence; they are
    not live market data and do not imply future performance.
    """
    case_specs = {
        "hyp_a_low_vol_dividend_defensive": [
            ("2025-01-03", "600000.SH", 10.0, 10.35, -0.025, []),
            ("2025-01-10", "601318.SH", 40.0, 40.80, -0.031, []),
            ("2025-01-17", "000001.SZ", 12.0, 11.88, -0.052, ["dividend_trap_watch"]),
            ("2025-01-24", "600519.SH", 100.0, 102.20, -0.040, []),
        ],
        "hyp_a_value_quality_multifactor": [
            ("2025-02-07", "600036.SH", 35.0, 35.25, -0.062, []),
            ("2025-02-14", "000858.SZ", 90.0, 87.70, -0.095, ["max_drawdown_breach"]),
            ("2025-02-21", "002475.SZ", 28.0, 27.35, -0.083, ["quality_deterioration"]),
            ("2025-02-28", "601899.SH", 18.0, 18.10, -0.070, []),
        ],
        "hyp_h_smart_beta_multifactor": [
            ("2025-03-07", "00700.HK", 320.0, 319.0, -0.085, ["regime_shift"]),
            ("2025-03-14", "00005.HK", 60.0, 59.2, -0.092, ["currency_context"]),
            ("2025-03-21", "01299.HK", 52.0, 52.4, -0.076, []),
            ("2025-03-28", "03690.HK", 110.0, 106.0, -0.112, ["event_risk_block"]),
        ],
        "hyp_h_low_vol_dividend": [
            ("2025-04-04", "00002.HK", 42.0, 42.75, -0.035, []),
            ("2025-04-11", "00003.HK", 6.0, 6.08, -0.028, []),
            ("2025-04-18", "01038.HK", 38.0, 37.80, -0.055, ["event_risk_watch"]),
            ("2025-04-25", "00823.HK", 36.0, 36.65, -0.041, []),
        ],
        "hyp_us_value_quality_momentum": [
            ("2025-05-02", "MSFT", 420.0, 428.0, -0.045, []),
            ("2025-05-09", "AAPL", 190.0, 192.4, -0.052, []),
            ("2025-05-16", "NVDA", 90.0, 93.2, -0.068, ["crowding_risk_note"]),
            ("2025-05-23", "GOOGL", 170.0, 168.5, -0.055, []),
        ],
        "hyp_us_low_vol_risk_overlay": [
            ("2025-06-06", "JNJ", 150.0, 150.8, -0.042, []),
            ("2025-06-13", "PG", 165.0, 163.1, -0.071, ["valuation_context"]),
            ("2025-06-20", "KO", 62.0, 61.4, -0.052, []),
            ("2025-06-27", "PEP", 175.0, 170.0, -0.105, ["max_drawdown_breach"]),
        ],
    }
    cases: list[HistoricalStrategyCase] = []
    for hypothesis in hypotheses:
        strategy_id = _candidate_id(hypothesis.hypothesis_id)
        for index, (date, symbol, entry, exit_, drawdown, flags) in enumerate(case_specs[hypothesis.hypothesis_id], start=1):
            cases.append(
                HistoricalStrategyCase(
                    case_id=f"{strategy_id}_case_{index:03d}",
                    strategy_id=strategy_id,
                    date=date,
                    symbol=symbol,
                    market=hypothesis.market,
                    entry_price=entry,
                    exit_price=exit_,
                    max_drawdown=drawdown,
                    risk_flags=flags,
                    factor_values={"fixture_factor_score": float(index)},
                    evidence_ref=f"v2_4_b_hypothesis:{hypothesis.hypothesis_id}",
                )
            )
    return cases


def build_hypothesis_sandbox_report(
    hypotheses: Iterable[StrategySandboxHypothesis],
    *,
    run_id: str,
    command: str | None = None,
    historical_cache_file_count: int = 0,
) -> dict:
    hypothesis_list = list(hypotheses)
    candidates = strategy_candidates_from_hypotheses(hypothesis_list)
    cases = fixture_historical_cases_for_hypotheses(hypothesis_list)
    report = build_strategy_sandbox_report(
        candidates,
        cases,
        run_id=run_id,
        command=command,
        historical_cache_file_count=historical_cache_file_count,
    )
    strategy_to_hypothesis = {
        _candidate_id(hypothesis.hypothesis_id): hypothesis.hypothesis_id for hypothesis in hypothesis_list
    }
    report["acceptance_target"] = "V2.4-C Historical Sandbox Run For Research Hypotheses"
    report["summary"]["hypothesis_count"] = len(hypothesis_list)
    report["summary"]["passing_hypotheses"] = [
        strategy_to_hypothesis[strategy_id] for strategy_id in report["summary"]["passing_strategies"]
    ]
    report["summary"]["failing_hypotheses"] = [
        strategy_to_hypothesis[strategy_id] for strategy_id in report["summary"]["failing_strategies"]
    ]
    report["strategy_to_hypothesis"] = strategy_to_hypothesis
    report["safety"]["hypothesis_only_until_suggestion_gate"] = True
    return report

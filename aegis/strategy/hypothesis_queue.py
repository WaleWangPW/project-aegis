"""Build sandbox hypothesis queues from strategy research sources."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from aegis.models.strategy_hypothesis import StrategySandboxHypothesis, StrategySandboxHypothesisQueue
from aegis.models.strategy_research import StrategyResearchRecord

SCHEMA_VERSION = "strategy_sandbox_hypothesis_queue.v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _refs_for(
    records: Iterable[StrategyResearchRecord],
    *,
    market: str,
    families: set[str],
) -> list[str]:
    refs: list[str] = []
    for record in records:
        if market not in record.markets:
            continue
        if families.intersection(set(record.strategy_families)):
            refs.append(record.research_id)
    return sorted(set(refs))


def _content_hash(hypothesis: StrategySandboxHypothesis) -> str:
    stable = {
        "hypothesis_id": hypothesis.hypothesis_id,
        "market": hypothesis.market,
        "strategy_families": hypothesis.strategy_families,
        "thesis": hypothesis.thesis,
        "source_research_ids": hypothesis.source_research_ids,
        "proposed_universe": hypothesis.proposed_universe,
        "proposed_entry_logic": hypothesis.proposed_entry_logic,
        "proposed_risk_controls": hypothesis.proposed_risk_controls,
    }
    return hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def build_strategy_sandbox_hypotheses(
    records: Iterable[StrategyResearchRecord],
    *,
    created_at: str | None = None,
) -> list[StrategySandboxHypothesis]:
    record_list = list(records)
    created = created_at or _now_iso()
    specs = [
        {
            "hypothesis_id": "hyp_a_low_vol_dividend_defensive",
            "title": "A-share low-volatility dividend defensive hypothesis",
            "market": "A",
            "families": ["low_volatility", "dividend", "risk_overlay"],
            "ref_families": {"low_volatility", "dividend", "risk_overlay"},
            "thesis": "A-share names with lower realized volatility and stronger dividend profile may reduce drawdown while preserving acceptable forward return.",
            "universe": "A-share liquid large/mid cap universe with dividend history and volatility data.",
            "entry": ["rank by dividend yield sustainability", "filter low realized volatility", "reject risk-vetoed names"],
            "exit": ["20 trading-day sandbox review", "exit on drawdown breach or risk veto"],
            "risk": ["liquidity_filter", "max_drawdown_floor", "dividend_trap_check", "risk_veto"],
            "metrics": ["sample_count", "win_rate", "average_return", "max_drawdown", "risk_flag_counts"],
        },
        {
            "hypothesis_id": "hyp_a_value_quality_multifactor",
            "title": "A-share value quality multi-factor hypothesis",
            "market": "A",
            "families": ["value", "quality", "multi_factor"],
            "ref_families": {"value", "quality", "multi_factor"},
            "thesis": "A-share candidates that combine reasonable valuation with profitability and cash-flow quality may outperform single-factor value screens.",
            "universe": "A-share liquid names with valuation, profitability, leverage, and cash-flow fields.",
            "entry": ["require valuation reasonableness", "require profitability/quality confirmation", "avoid unresolved data gaps"],
            "exit": ["20 trading-day sandbox review", "downgrade if quality evidence deteriorates"],
            "risk": ["liquidity_filter", "financial_quality_check", "policy_event_note", "risk_veto"],
            "metrics": ["sample_count", "win_rate", "average_return", "max_drawdown", "data_gap_count"],
        },
        {
            "hypothesis_id": "hyp_h_smart_beta_multifactor",
            "title": "Hong Kong smart-beta multi-factor hypothesis",
            "market": "H",
            "families": ["value", "quality", "momentum", "low_volatility", "dividend", "multi_factor"],
            "ref_families": {"value", "quality", "momentum", "low_volatility", "dividend", "multi_factor"},
            "thesis": "Hong Kong smart-beta factors may require regime-aware blending rather than one dominant factor.",
            "universe": "Hong Kong liquid shares with factor data and Stock Connect context where available.",
            "entry": ["combine value/quality/momentum/low-volatility evidence", "segment by market regime", "require liquidity"],
            "exit": ["20 trading-day sandbox review", "review on regime shift"],
            "risk": ["stock_connect_awareness", "liquidity_filter", "event_risk_block", "currency_context_note"],
            "metrics": ["sample_count", "win_rate", "average_return", "max_drawdown", "regime_split_return"],
        },
        {
            "hypothesis_id": "hyp_h_low_vol_dividend",
            "title": "Hong Kong low-volatility dividend hypothesis",
            "market": "H",
            "families": ["low_volatility", "dividend", "risk_overlay"],
            "ref_families": {"low_volatility", "dividend", "risk_overlay"},
            "thesis": "Hong Kong lower-volatility dividend candidates may be useful defensive ideas if liquidity and event risks are controlled.",
            "universe": "Hong Kong liquid dividend-paying shares with volatility history.",
            "entry": ["filter dividend names", "rank lower volatility", "reject event-risk blocked candidates"],
            "exit": ["20 trading-day sandbox review", "exit on dividend risk or drawdown breach"],
            "risk": ["liquidity_filter", "event_risk_block", "max_drawdown_floor", "manual_execution_only"],
            "metrics": ["sample_count", "win_rate", "average_return", "max_drawdown", "risk_flag_counts"],
        },
        {
            "hypothesis_id": "hyp_us_value_quality_momentum",
            "title": "U.S. value quality momentum blend hypothesis",
            "market": "US",
            "families": ["value", "quality", "momentum", "multi_factor"],
            "ref_families": {"value", "quality", "momentum", "multi_factor"},
            "thesis": "U.S. candidates with complementary value, quality, and momentum evidence may be more robust than a single-factor ranking.",
            "universe": "U.S. large/mid cap universe with factor and price history.",
            "entry": ["require value signal", "confirm quality/profitability", "confirm positive momentum"],
            "exit": ["20 trading-day sandbox review", "exit if momentum breaks or quality evidence weakens"],
            "risk": ["sector_concentration_check", "drawdown_floor", "quality_overlay", "crowding_risk_note"],
            "metrics": ["sample_count", "win_rate", "average_return", "max_drawdown", "turnover_proxy"],
        },
        {
            "hypothesis_id": "hyp_us_low_vol_risk_overlay",
            "title": "U.S. low-volatility risk-overlay hypothesis",
            "market": "US",
            "families": ["low_volatility", "value", "momentum", "risk_overlay"],
            "ref_families": {"low_volatility", "value", "momentum", "risk_overlay"},
            "thesis": "Low-volatility U.S. candidates may need valuation and momentum context to avoid cycle-specific underperformance.",
            "universe": "U.S. large cap universe with volatility, valuation, and momentum history.",
            "entry": ["rank lower volatility", "check valuation context", "check momentum context"],
            "exit": ["20 trading-day sandbox review", "exit on drawdown or factor deterioration"],
            "risk": ["max_drawdown_floor", "valuation_context_check", "momentum_context_check", "risk_veto"],
            "metrics": ["sample_count", "win_rate", "average_return", "max_drawdown", "risk_flag_counts"],
        },
    ]

    hypotheses: list[StrategySandboxHypothesis] = []
    for spec in specs:
        refs = _refs_for(record_list, market=spec["market"], families=spec["ref_families"])
        hypotheses.append(
            StrategySandboxHypothesis(
                hypothesis_id=spec["hypothesis_id"],
                title=spec["title"],
                market=spec["market"],
                strategy_families=spec["families"],
                thesis=spec["thesis"],
                source_research_ids=refs,
                proposed_universe=spec["universe"],
                proposed_entry_logic=spec["entry"],
                proposed_exit_logic=spec["exit"],
                proposed_risk_controls=spec["risk"],
                proposed_metrics=spec["metrics"],
                requires_sandbox=True,
                auto_applied=False,
                user_facing_suggestion_allowed=False,
                created_at=created,
            )
        )
    return hypotheses


def build_strategy_sandbox_hypothesis_queue(
    records: Iterable[StrategyResearchRecord],
    *,
    created_at: str | None = None,
) -> dict:
    hypotheses = build_strategy_sandbox_hypotheses(records, created_at=created_at)
    market_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    for hypothesis in hypotheses:
        market_counts.update([hypothesis.market])
        family_counts.update(hypothesis.strategy_families)

    queue = StrategySandboxHypothesisQueue(
        schema_version=SCHEMA_VERSION,
        generated_at=_now_iso(),
        hypothesis_count=len(hypotheses),
        market_coverage=dict(sorted(market_counts.items())),
        strategy_family_coverage=dict(sorted(family_counts.items())),
        hypotheses=hypotheses,
        safety={
            "hypothesis_only": True,
            "requires_sandbox": True,
            "auto_applied": False,
            "user_facing_suggestion_allowed": False,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_strategy_auto_mutation": True,
            "no_production_records_mutation": True,
        },
    )
    payload = queue.model_dump()
    payload["hypothesis_hashes"] = {hypothesis.hypothesis_id: _content_hash(hypothesis) for hypothesis in hypotheses}
    return payload


def write_strategy_sandbox_hypothesis_queue(records: Iterable[StrategyResearchRecord], output_path: Path) -> dict:
    payload = build_strategy_sandbox_hypothesis_queue(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload

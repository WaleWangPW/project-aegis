"""A-share strategy hypotheses built from read-only Tushare source probes."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from aegis.models.strategy_hypothesis import StrategySandboxHypothesis, StrategySandboxHypothesisQueue

SCHEMA_VERSION = "a_share_tushare_source_hypothesis_queue.v1"
SOURCE_RESEARCH_ID = "tushare_a_share_strategy_source_probe"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _endpoint_map(probe_report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in probe_report.get("modules", []):
        grouped.setdefault(str(item.get("module_id")), []).append(item)
    return grouped


def _module_passes(grouped: dict[str, list[dict[str, Any]]], module_id: str, endpoints: set[str]) -> bool:
    rows = grouped.get(module_id, [])
    present = {str(item.get("endpoint")) for item in rows if item.get("status") == "PASS"}
    return endpoints.issubset(present)


def _refs(probe_report: dict[str, Any], module_id: str, endpoints: list[str]) -> list[str]:
    latest = probe_report.get("latest_trade_date") or "unknown_date"
    return [f"{SOURCE_RESEARCH_ID}:{module_id}:{endpoint}:{latest}" for endpoint in endpoints]


def _content_hash(hypothesis: StrategySandboxHypothesis) -> str:
    stable = {
        "hypothesis_id": hypothesis.hypothesis_id,
        "market": hypothesis.market,
        "strategy_families": hypothesis.strategy_families,
        "source_research_ids": hypothesis.source_research_ids,
        "thesis": hypothesis.thesis,
        "proposed_entry_logic": hypothesis.proposed_entry_logic,
        "proposed_risk_controls": hypothesis.proposed_risk_controls,
    }
    return hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def build_a_share_tushare_source_hypotheses(
    probe_report: dict[str, Any],
    *,
    created_at: str | None = None,
) -> list[StrategySandboxHypothesis]:
    """Build sandbox-only hypotheses from PASS Tushare modules.

    This function deliberately ignores blocked modules. It creates research
    hypotheses only; it never changes live selection ranking or writes trades.
    """

    created = created_at or _now_iso()
    grouped = _endpoint_map(probe_report)
    specs = [
        {
            "module_id": "capital_flow",
            "endpoints": ["moneyflow"],
            "hypothesis_id": "hyp_a_tushare_capital_flow_accumulation",
            "title": "A-share capital-flow accumulation hypothesis",
            "families": ["capital_flow", "momentum", "risk_overlay"],
            "thesis": "A-share candidates with persistent large-order inflow and non-extreme price extension may produce better short-cycle simulation results than price momentum alone.",
            "universe": "A-share liquid names with Tushare moneyflow rows and daily price/factor context.",
            "entry": [
                "require recent moneyflow PASS evidence",
                "rank large-order and net inflow persistence",
                "reject names where retail chase risk dominates the move",
            ],
            "exit": [
                "20 trading-day sandbox review",
                "downgrade if capital flow reverses before price confirms",
            ],
            "risk": ["no_realtime_trade_claim", "liquidity_filter", "overheated_momentum_downgrade", "risk_veto"],
            "metrics": ["sample_count", "win_rate", "average_return", "max_drawdown", "flow_reversal_rate"],
        },
        {
            "module_id": "dragon_tiger_hot_money",
            "endpoints": ["top_list", "top_inst"],
            "hypothesis_id": "hyp_a_tushare_dragon_tiger_seat_confirmation",
            "title": "A-share dragon-tiger hot-money seat confirmation hypothesis",
            "families": ["hot_money", "momentum", "risk_overlay"],
            "thesis": "龙虎榜上榜标的只有在买卖席位结构改善、机构或高质量席位参与、且不过度拥挤时，才进入短周期模拟研究。",
            "universe": "A-share top_list/top_inst names with matching daily factor and price context.",
            "entry": [
                "require top_list and top_inst PASS evidence",
                "separate institutional net buy from pure hot-money relay",
                "use seat concentration as a warning, not a buy reason",
            ],
            "exit": ["5-20 trading-day sandbox review", "downgrade if follow-through volume or price confirmation fails"],
            "risk": ["one_day_spike_filter", "seat_crowding_warning", "limit_up_chase_block", "risk_veto"],
            "metrics": ["follow_through_rate", "win_rate", "average_return", "max_drawdown", "gap_down_frequency"],
        },
        {
            "module_id": "institutional_ownership",
            "endpoints": ["top10_holders", "top10_floatholders"],
            "hypothesis_id": "hyp_a_tushare_institutional_ownership_stability",
            "title": "A-share institutional ownership stability hypothesis",
            "families": ["institutional_ownership", "quality", "risk_overlay"],
            "thesis": "机构和前十大流通股东稳定增持可以作为中期质量线索，但必须按披露日防前视，不允许把未来披露提前用于选股。",
            "universe": "A-share names with disclosed top10 holder/floatholder records and point-in-time report dates.",
            "entry": [
                "require top10 holder and floatholder PASS evidence",
                "use disclosure date as evidence date",
                "prefer stable concentration improvement over sudden crowding",
            ],
            "exit": ["quarterly disclosure sandbox review", "downgrade when concentration deteriorates or crowding risk rises"],
            "risk": ["point_in_time_disclosure_guard", "crowding_risk_note", "liquidity_filter", "risk_veto"],
            "metrics": ["disclosure_lag_days", "win_rate", "average_return", "max_drawdown", "concentration_change"],
        },
        {
            "module_id": "holder_concentration",
            "endpoints": ["stk_holdernumber"],
            "hypothesis_id": "hyp_a_tushare_holder_concentration_improvement",
            "title": "A-share holder concentration improvement hypothesis",
            "families": ["holder_concentration", "quality", "multi_factor"],
            "thesis": "股东人数下降和筹码集中改善可以作为研究线索，但必须与基本面质量和价格趋势共同验证。",
            "universe": "A-share names with holder-number history, quality fields, and daily factor context.",
            "entry": [
                "require holder-number PASS evidence",
                "rank sustained holder count decline rather than one-off noise",
                "combine with quality and liquidity filters",
            ],
            "exit": ["quarterly disclosure sandbox review", "downgrade when holder count expands materially"],
            "risk": ["disclosure_delay_guard", "small_float_crowding_check", "quality_overlay", "risk_veto"],
            "metrics": ["holder_count_change", "sample_count", "win_rate", "average_return", "max_drawdown"],
        },
        {
            "module_id": "factor_base",
            "endpoints": ["stk_factor", "daily_basic"],
            "hypothesis_id": "hyp_a_tushare_factor_liquidity_quality_overlay",
            "title": "A-share factor liquidity quality overlay hypothesis",
            "families": ["multi_factor", "quality", "momentum", "risk_overlay"],
            "thesis": "Tushare stk_factor and daily_basic should become the A-share base layer for liquidity, valuation heat, turnover, and short-cycle momentum guards.",
            "universe": "A-share daily_basic/stk_factor universe with sufficient liquidity and non-stale price evidence.",
            "entry": [
                "require daily_basic and stk_factor PASS evidence",
                "filter liquidity and turnover before any thematic ranking",
                "use valuation heat and volatility as risk overlays",
            ],
            "exit": ["20 trading-day sandbox review", "downgrade if factor evidence becomes stale or risk overlay fails"],
            "risk": ["liquidity_filter", "valuation_overheat_check", "stale_price_check", "risk_veto"],
            "metrics": ["liquidity_pass_rate", "win_rate", "average_return", "max_drawdown", "overheat_downgrade_count"],
        },
        {
            "module_id": "governance",
            "endpoints": ["stk_rewards"],
            "hypothesis_id": "hyp_a_tushare_governance_reward_alignment",
            "title": "A-share governance and reward-alignment hypothesis",
            "families": ["governance", "quality", "risk_overlay"],
            "thesis": "高管薪酬和持股信息只能作为治理风险线索，用于降权或复核，不单独产生买入候选。",
            "universe": "A-share names with governance/reward rows and quality context.",
            "entry": [
                "require stk_rewards PASS evidence",
                "use governance information as a review overlay",
                "never promote a candidate on governance data alone",
            ],
            "exit": ["governance event review", "downgrade on governance inconsistency or disclosure concerns"],
            "risk": ["governance_red_flag_review", "not_standalone_signal", "manual_review_required", "risk_veto"],
            "metrics": ["governance_flag_count", "downgrade_rate", "win_rate", "average_return", "max_drawdown"],
        },
    ]

    hypotheses: list[StrategySandboxHypothesis] = []
    for spec in specs:
        endpoints = set(spec["endpoints"])
        if not _module_passes(grouped, spec["module_id"], endpoints):
            continue
        hypotheses.append(
            StrategySandboxHypothesis(
                hypothesis_id=spec["hypothesis_id"],
                title=spec["title"],
                market="A",
                strategy_families=spec["families"],
                thesis=spec["thesis"],
                source_research_ids=_refs(probe_report, spec["module_id"], spec["endpoints"]),
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


def build_a_share_tushare_source_hypothesis_queue(
    probe_report: dict[str, Any],
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    hypotheses = build_a_share_tushare_source_hypotheses(probe_report, created_at=created_at)
    market_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    for hypothesis in hypotheses:
        market_counts.update([hypothesis.market])
        family_counts.update(hypothesis.strategy_families)

    source_modules = probe_report.get("modules", [])
    blocked = [
        {
            "module_id": item.get("module_id"),
            "module_name": item.get("module_name"),
            "endpoint": item.get("endpoint"),
            "status": item.get("status"),
            "reason": item.get("error_message"),
        }
        for item in source_modules
        if item.get("status") != "PASS"
    ]
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
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values": True,
            "no_raw_tushare_payload": True,
            "no_production_records_mutation": True,
        },
    )
    payload = queue.model_dump()
    payload.update(
        {
            "source_probe_status": probe_report.get("overall_status"),
            "source_latest_trade_date": probe_report.get("latest_trade_date"),
            "source_endpoint_count": len(source_modules),
            "blocked_or_skipped_sources": blocked,
            "hypothesis_hashes": {item.hypothesis_id: _content_hash(item) for item in hypotheses},
            "next_step": "Run historical sandbox for these A-share source hypotheses before ranking or recommendation use.",
        }
    )
    return payload

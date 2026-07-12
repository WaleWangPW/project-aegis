"""Canonical strategy research source catalog for A/H/US strategy discovery."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from aegis.models.strategy_research import StrategyResearchRecord


def canonical_strategy_research_records() -> list[StrategyResearchRecord]:
    """Return summary-only research records that can seed sandbox hypotheses."""
    return [
        StrategyResearchRecord(
            research_id="catalog_spdji_a_share_factor",
            title="Examining Factor Strategies in China's A-Share Market",
            source_type="index_provider",
            publisher="S&P Dow Jones Indices",
            url="https://www.spglobal.com/spdji/en/documents/research/research-examining-factor-strategies-in-china-a-share-market.pdf",
            published_at="2016",
            markets=["A"],
            strategy_families=["size", "value", "low_volatility", "momentum", "quality", "dividend", "multi_factor"],
            evidence_level="institutional_research",
            summary="Studies size, value, low-volatility, momentum, quality, dividend, and multi-factor approaches in China A-shares.",
            implications=[
                "Build A-share sandbox cases for each single factor before blending factors.",
                "Require liquidity and turnover checks before any user-facing suggestion.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_msci_china_a_factor_2025",
            title="Are You Really Capturing the Right Factors?",
            source_type="index_provider",
            publisher="MSCI",
            url="https://www.msci.com/research-and-insights/paper/are-you-really-capturing-the-right-factors-unlocking-deeper-insights-in-china-a-share-factor-investing",
            published_at="2025",
            markets=["A"],
            strategy_families=["dividend", "low_volatility", "quality", "value", "multi_factor"],
            evidence_level="institutional_research",
            summary="MSCI discusses why China A-share factor behavior can differ from global factor hierarchies.",
            implications=[
                "Do not import U.S. factor thresholds directly into A-share screening.",
                "Prioritize A-share high-dividend and low-volatility sandbox variants.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_spdji_a_low_vol_high_dividend",
            title="Blending Low Volatility with Dividend Yield in the China A-Share Market",
            source_type="index_provider",
            publisher="S&P Dow Jones Indices",
            url="https://www.spglobal.com/spdji/en/documents/research/research-blending-low-volatility-with-dividend-yield-in-the-china-a-share-market.pdf",
            published_at="2019",
            markets=["A"],
            strategy_families=["low_volatility", "dividend", "risk_overlay"],
            evidence_level="institutional_research",
            summary="Examines combining low volatility and high dividend yield in China A-share large-cap equities.",
            implications=[
                "Create defensive A-share sandbox variants that combine volatility and dividend filters.",
                "Treat drawdown reduction as a separate acceptance metric, not just return ranking.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_panagora_china_a_factor",
            title="Factor Investing in the China A-Share Market",
            source_type="asset_manager",
            publisher="PanAgora / CAIA",
            url="https://caia.org/sites/default/files/factor_investing_in_the_china_a-share_market.pdf",
            published_at="2018",
            markets=["A"],
            strategy_families=["value", "quality", "momentum", "multi_factor"],
            evidence_level="institutional_research",
            summary="Discusses A-share factor investing with emphasis on market history, investor behavior, regulation, and governance.",
            implications=[
                "Attach governance and policy-risk context to A-share candidate review.",
                "Do not treat A-share factor research as purely mechanical ranking.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_spdji_hk_smart_beta",
            title="How Smart Beta Strategies Work in the Hong Kong Market",
            source_type="index_provider",
            publisher="S&P Dow Jones Indices",
            url="https://www.spglobal.com/spdji/en/documents/research/research-how-smart-beta-strategies-work-in-the-hong-kong-market.pdf",
            published_at="2017",
            markets=["H"],
            strategy_families=["size", "value", "low_volatility", "momentum", "quality", "dividend", "multi_factor"],
            evidence_level="institutional_research",
            summary="Examines six major smart-beta factors in Hong Kong equities and their behavior across market regimes.",
            implications=[
                "Hong Kong sandbox cases must include regime segmentation.",
                "Liquidity and Stock Connect context should be tracked before suggestions.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_hsi_smart_beta_index_series",
            title="Hang Seng Smart Beta Index Series",
            source_type="index_provider",
            publisher="Hang Seng Indexes",
            url="https://www.hsi.com.hk/static/uploads/contents/en/dl_centre/brochures/HSIL_Smart_Beta_Brochure.pdf",
            markets=["H"],
            strategy_families=["value", "momentum", "quality", "dividend", "low_volatility", "size", "multi_factor"],
            evidence_level="institutional_research",
            summary="Describes Hang Seng smart beta index construction around value, momentum, quality, yield, low volatility, and size.",
            implications=[
                "Use index methodology as a transparent benchmark for Hong Kong factor candidates.",
                "Keep index-style rules separate from discretionary recommendation logic.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_fama_french_five_factor",
            title="A Five-Factor Asset Pricing Model",
            source_type="academic",
            publisher="Fama and French",
            url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2287202",
            published_at="2014",
            markets=["US", "GLOBAL"],
            strategy_families=["size", "value", "quality"],
            evidence_level="primary_research",
            summary="Extends market, size, and value with profitability and investment factors for explaining average stock returns.",
            implications=[
                "Map profitability and conservative investment into U.S. quality strategy candidates.",
                "Use academic factors as hypotheses, not direct buy/sell rules.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_ken_french_factor_library",
            title="Fama/French 5 Factors Data Library",
            source_type="academic",
            publisher="Kenneth R. French Data Library",
            url="https://mba.tuck.dartmouth.edu/pages/faculty/Ken.french/Data_Library/f-f_5_factors_2x3.html",
            markets=["US", "GLOBAL"],
            strategy_families=["size", "value", "quality"],
            evidence_level="primary_research",
            summary="Documents construction of the five Fama/French factors from size, book-to-market, profitability, and investment portfolios.",
            implications=[
                "Use as factor-definition reference when translating U.S. academic factors into Aegis fields.",
                "Do not mix return-factor data with user recommendation records.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_msci_factor_indexes",
            title="MSCI Factor Indexes",
            source_type="index_provider",
            publisher="MSCI",
            url="https://www.msci.com/indexes/category/factor-indexes",
            markets=["US", "GLOBAL"],
            strategy_families=["value", "quality", "momentum", "low_volatility", "size", "dividend", "multi_factor"],
            evidence_level="institutional_research",
            summary="Describes transparent factor-index exposure to value, quality, momentum, low volatility, size, yield, and multi-factor ideas.",
            implications=[
                "Keep factor definitions explicit and auditable in Strategy Library records.",
                "Compare Aegis factor candidates against index-style factor families.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_research_affiliates_vqm",
            title="Why Value, Quality, and Momentum Belong Together",
            source_type="asset_manager",
            publisher="Research Affiliates",
            url="https://www.researchaffiliates.com/content/dam/ra/publications/pdf/1110-why-value-quality-and-momentum-belong-together.pdf",
            published_at="2026-03-10",
            markets=["US", "GLOBAL"],
            strategy_families=["value", "quality", "momentum", "multi_factor"],
            evidence_level="institutional_research",
            summary="Discusses combining value, quality, and momentum signals in systematic active equity selection.",
            implications=[
                "VQM blends should preserve separate evidence for value, quality, and momentum.",
                "Blended strategy proposals must still pass historical sandbox gates.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_msci_low_volatility_construction",
            title="Constructing Low Volatility Strategies",
            source_type="index_provider",
            publisher="MSCI",
            url="https://www.msci.com/documents/10199/95bba81c-4ab0-4698-8ea1-ab4f515afc38",
            markets=["US", "GLOBAL"],
            strategy_families=["low_volatility", "risk_overlay"],
            evidence_level="institutional_research",
            summary="Discusses practical construction questions for low-volatility strategies as a systematic factor exposure.",
            implications=[
                "Low-volatility candidates should be evaluated on drawdown and volatility, not only average return.",
                "Add risk-overlay labels before such candidates can reach Suggestion Gate.",
            ],
        ),
        StrategyResearchRecord(
            research_id="catalog_aqr_low_vol_cycles",
            title="Low-Volatility Cycles",
            source_type="asset_manager",
            publisher="AQR / Financial Analysts Journal",
            url="https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/Low-Volatility-Cycles-The-Influence-of-Valuation-and-Momentum-on-Low-Volatility-Portfolios.pdf",
            published_at="2015",
            markets=["US", "GLOBAL"],
            strategy_families=["low_volatility", "value", "momentum", "risk_overlay"],
            evidence_level="institutional_research",
            summary="Studies how valuation and momentum can influence low-volatility portfolio behavior across cycles.",
            implications=[
                "Risk overlays should track valuation and momentum context around low-volatility names.",
                "Sandbox should compare pure low-volatility against valuation-aware variants.",
            ],
        ),
    ]


def summarize_catalog(records: Iterable[StrategyResearchRecord]) -> dict:
    record_list = list(records)
    market_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    publisher_counts: Counter[str] = Counter()
    for record in record_list:
        market_counts.update(record.markets)
        family_counts.update(record.strategy_families)
        publisher_counts.update([record.publisher])
    return {
        "record_count": len(record_list),
        "market_coverage": dict(sorted(market_counts.items())),
        "strategy_family_coverage": dict(sorted(family_counts.items())),
        "publisher_coverage": dict(sorted(publisher_counts.items())),
        "research_ids": [record.research_id for record in record_list],
        "safety": {
            "summary_only": all(record.retention_policy == "summary_only" for record in record_list),
            "raw_text_not_stored": all(not record.raw_text_stored for record in record_list),
            "requires_sandbox_before_suggestion": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_strategy_auto_mutation": True,
        },
    }

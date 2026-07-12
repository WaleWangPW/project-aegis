"""Strategy research ingestion for V2.2-A."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from aegis.models.strategy_research import StrategyResearchCorpus, StrategyResearchRecord

SCHEMA_VERSION = "strategy_research_corpus.v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _content_hash(record: StrategyResearchRecord) -> str:
    stable = {
        "research_id": record.research_id,
        "title": record.title,
        "publisher": record.publisher,
        "url": record.url,
        "markets": record.markets,
        "strategy_families": record.strategy_families,
        "summary": record.summary,
    }
    return hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def build_strategy_research_corpus(records: Iterable[StrategyResearchRecord]) -> dict:
    record_list = list(records)
    market_coverage: dict[str, int] = {}
    family_coverage: dict[str, int] = {}
    for record in record_list:
        for market in record.markets:
            market_coverage[market] = market_coverage.get(market, 0) + 1
        for family in record.strategy_families:
            family_coverage[family] = family_coverage.get(family, 0) + 1

    corpus = StrategyResearchCorpus(
        schema_version=SCHEMA_VERSION,
        generated_at=_now_iso(),
        record_count=len(record_list),
        market_coverage=market_coverage,
        strategy_family_coverage=family_coverage,
        records=record_list,
        safety={
            "summary_only": True,
            "raw_text_not_stored": True,
            "no_secret_storage": True,
            "no_paywall_bypass": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_auto_mutation": True,
        },
    )
    payload = corpus.model_dump()
    payload["record_hashes"] = {record.research_id: _content_hash(record) for record in record_list}
    return payload


def write_strategy_research_corpus(records: Iterable[StrategyResearchRecord], output_path: Path) -> dict:
    payload = build_strategy_research_corpus(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload

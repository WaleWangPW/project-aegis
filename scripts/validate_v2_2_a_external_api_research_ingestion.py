#!/usr/bin/env python3
"""Validate Project Aegis V2.2-A External API Connector and Strategy Research Ingestion."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis.external_sources.api_connector import evaluate_api_connector_registry  # noqa: E402
from aegis.models.external_api import ExternalAPIConnectorSpec  # noqa: E402
from aegis.models.strategy_research import StrategyResearchRecord  # noqa: E402
from aegis.strategy.research_ingestion import write_strategy_research_corpus  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "processed" / "v2_2_a_acceptance"
DEFAULT_REPORTS_DIR = ROOT / "data" / "reports"

PASS_MARKER = "V2_2_A_EXTERNAL_API_RESEARCH_INGESTION_PASS.marker"
FAIL_MARKER = "V2_2_A_EXTERNAL_API_RESEARCH_INGESTION_FAIL.marker"
REPORT_JSON = "v2_2_a_external_api_research_ingestion_latest.json"
REPORT_MD = "v2_2_a_external_api_research_ingestion_latest.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _run_id() -> str:
    return "v2_2_a_external_api_research_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fixture_connectors() -> list[ExternalAPIConnectorSpec]:
    return [
        ExternalAPIConnectorSpec(
            connector_id="api_sec_companyfacts",
            name="SEC Companyfacts API",
            provider_type="official_regulator",
            markets=["US"],
            base_url="https://data.sec.gov/api/xbrl/companyfacts/",
            auth_method="none",
            license_status="not_required",
            retention_policy="summary_only",
            allowed_purposes=["official_filings_context", "evidence_metadata"],
            can_connect=True,
            notes="Official regulator API; no API key.",
        ),
        ExternalAPIConnectorSpec(
            connector_id="api_user_research_approved_env",
            name="User Approved Strategy Research API",
            provider_type="user_provided_research_api",
            markets=["A", "H", "US"],
            base_url="https://api.example-research-provider.invalid/v1/strategy-notes",
            auth_method="env_var",
            required_env_vars=["AEGIS_RESEARCH_API_KEY"],
            license_status="approved",
            retention_policy="summary_only",
            allowed_purposes=["strategy_research_ingestion"],
            can_connect=True,
            notes="Stores env var name only; the actual key must stay outside repo and Vault.",
        ),
        ExternalAPIConnectorSpec(
            connector_id="api_broker_forbidden",
            name="Forbidden Broker API",
            provider_type="broker_api",
            markets=["US"],
            base_url="https://broker.example.invalid/api",
            auth_method="env_var",
            required_env_vars=["BROKER_API_KEY"],
            license_status="forbidden",
            retention_policy="no_storage",
            allowed_purposes=["order_placement"],
            can_connect=False,
            notes="Broker access is outside Aegis scope.",
        ),
        ExternalAPIConnectorSpec(
            connector_id="api_trading_webhook_forbidden",
            name="Forbidden Trading Webhook",
            provider_type="trading_webhook",
            markets=["GLOBAL"],
            base_url="https://webhook.example.invalid/trade",
            auth_method="none",
            license_status="forbidden",
            retention_policy="no_storage",
            allowed_purposes=["trade_execution"],
            can_connect=False,
            notes="Webhooks that can trade are forbidden.",
        ),
    ]


def _fixture_research_records() -> list[StrategyResearchRecord]:
    return [
        StrategyResearchRecord(
            research_id="research_spdji_a_share_factor",
            title="Examining Factor Strategies in China's A-Share Market",
            source_type="index_provider",
            publisher="S&P Dow Jones Indices",
            url="https://www.spglobal.com/spdji/en/documents/research/research-examining-factor-strategies-in-china-a-share-market.pdf",
            published_at="2016",
            markets=["A"],
            strategy_families=["value", "low_volatility", "dividend", "quality", "momentum", "size"],
            evidence_level="institutional_research",
            summary="S&P DJI research studies common A-share factors including value, low volatility, dividend, quality, momentum, and size.",
            implications=[
                "A-share strategy candidates should test low-volatility, dividend, value, and quality factors separately.",
                "Factor evidence must be re-tested in Aegis historical sandbox before suggestions.",
            ],
        ),
        StrategyResearchRecord(
            research_id="research_spdji_hk_smart_beta",
            title="How Smart Beta Strategies Work in the Hong Kong Market",
            source_type="index_provider",
            publisher="S&P Dow Jones Indices",
            url="https://www.spglobal.com/spdji/en/documents/research/research-how-smart-beta-strategies-work-in-the-hong-kong-market.pdf",
            published_at="2017",
            markets=["H"],
            strategy_families=["value", "low_volatility", "dividend", "quality", "momentum", "size"],
            evidence_level="institutional_research",
            summary="S&P DJI research examines size, value, low-volatility, momentum, quality, and dividend factors in Hong Kong equities.",
            implications=[
                "Hong Kong candidates need liquidity and Stock Connect awareness.",
                "Regime checks should be attached before user-facing suggestions.",
            ],
        ),
        StrategyResearchRecord(
            research_id="research_msci_factor_indexes",
            title="MSCI Factor Indexes",
            source_type="index_provider",
            publisher="MSCI",
            url="https://www.msci.com/indexes/category/factor-indexes",
            markets=["GLOBAL", "US"],
            strategy_families=["value", "quality", "momentum", "low_volatility", "size", "dividend"],
            evidence_level="institutional_research",
            summary="MSCI describes factor indexes as transparent exposures to historically documented return drivers.",
            implications=[
                "Aegis factor candidates should stay explicit and auditable.",
                "Factor exposure is research context, not accepted strategy until sandbox PASS.",
            ],
        ),
        StrategyResearchRecord(
            research_id="research_fama_french_five_factor",
            title="A Five-Factor Asset Pricing Model",
            source_type="academic",
            publisher="Fama and French",
            url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2287202",
            published_at="2014",
            markets=["US", "GLOBAL"],
            strategy_families=["value", "quality", "size"],
            evidence_level="primary_research",
            summary="The five-factor model extends size and value with profitability and investment patterns in average stock returns.",
            implications=[
                "Quality/profitability factors can inform U.S. candidate construction.",
                "Academic factor evidence still requires local Aegis sandbox validation.",
            ],
        ),
        StrategyResearchRecord(
            research_id="research_ra_value_quality_momentum_2026",
            title="Why Value, Quality, and Momentum Belong Together",
            source_type="asset_manager",
            publisher="Research Affiliates",
            url="https://www.researchaffiliates.com/content/dam/ra/publications/pdf/1110-why-value-quality-and-momentum-belong-together.pdf",
            published_at="2026-03-10",
            markets=["US", "GLOBAL"],
            strategy_families=["value", "quality", "momentum", "multi_factor"],
            evidence_level="institutional_research",
            summary="Research Affiliates describes a systematic active equity process combining value, quality, and momentum signals.",
            implications=[
                "V2.1-B multi-factor candidates should preserve separate value, quality, and momentum evidence fields.",
                "Do not allow LLM-generated factor blends without acceptance evidence.",
            ],
        ),
        StrategyResearchRecord(
            research_id="research_msci_china_a_2025_factor",
            title="China A-share factor investing insights",
            source_type="index_provider",
            publisher="MSCI",
            url="https://www.msci.com/research-and-insights/paper/are-you-really-capturing-the-right-factors-unlocking-deeper-insights-in-china-a-share-factor-investing",
            published_at="2025",
            markets=["A"],
            strategy_families=["multi_factor", "quality", "value", "low_volatility"],
            evidence_level="institutional_research",
            summary="MSCI notes that China A-share factor premia can differ from developed and emerging-market factor behavior.",
            implications=[
                "A-share factors should not blindly reuse U.S. thresholds.",
                "Aegis should require market-specific sandbox acceptance.",
            ],
        ),
    ]


def run_acceptance(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    run_id: Optional[str] = None,
    command: Optional[str] = None,
) -> dict:
    run_id = run_id or _run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    connectors = _fixture_connectors()
    registry = evaluate_api_connector_registry(connectors)
    registry_json = run_dir / "external_api_connector_registry.json"
    registry_json.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    research_records = _fixture_research_records()
    corpus_json = run_dir / "strategy_research_corpus.json"
    corpus = write_strategy_research_corpus(research_records, corpus_json)

    decisions = {item["connector_id"]: item for item in registry["decisions"]}
    checks = {
        "official_api_allowed": decisions["api_sec_companyfacts"]["decision"] == "allow",
        "user_api_env_only_allowed": decisions["api_user_research_approved_env"]["decision"] == "allow",
        "broker_api_denied": decisions["api_broker_forbidden"]["decision"] == "deny",
        "trading_webhook_denied": decisions["api_trading_webhook_forbidden"]["decision"] == "deny",
        "env_var_names_only": registry["safety"]["env_var_names_only"] is True,
        "no_secret_values_stored": registry["safety"]["no_secret_values_stored"] is True,
        "research_covers_a_h_us": all(corpus["market_coverage"].get(market, 0) > 0 for market in ["A", "H", "US"]),
        "research_covers_core_factors": all(
            corpus["strategy_family_coverage"].get(family, 0) > 0
            for family in ["value", "quality", "momentum", "low_volatility", "dividend", "multi_factor"]
        ),
        "research_raw_text_not_stored": corpus["safety"]["raw_text_not_stored"] is True
        and all(not record.raw_text_stored for record in research_records),
        "research_hashes_present": len(corpus["record_hashes"]) == len(research_records),
        "no_real_trade_or_broker": registry["safety"]["no_real_trade"] is True
        and registry["safety"]["no_broker_api"] is True
        and corpus["safety"]["no_real_trade"] is True,
        "no_webhook": registry["safety"]["no_trading_webhook"] is True and corpus["safety"]["no_webhook"] is True,
        "no_strategy_auto_mutation": registry["safety"]["no_strategy_auto_mutation"] is True
        and corpus["safety"]["no_strategy_auto_mutation"] is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("V2.2-A acceptance checks failed: " + ", ".join(failed))

    report = {
        "overall_status": "PASS",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "command": command,
        "acceptance_target": "V2.2-A External API Connector and Strategy Research Ingestion",
        "isolated": True,
        "network_used": False,
        "production_records_written": False,
        "dashboard_contract_changed": False,
        "run_dir": str(run_dir),
        "api_registry_json": str(registry_json),
        "strategy_research_corpus_json": str(corpus_json),
        "checks": checks,
        "summary": {
            "connector_count": registry["connector_count"],
            "connector_allow_count": registry["allow_count"],
            "connector_deny_count": registry["deny_count"],
            "research_record_count": corpus["record_count"],
            "market_coverage": corpus["market_coverage"],
            "strategy_family_coverage": corpus["strategy_family_coverage"],
            "next_target": "V2.2-B API-backed Research Fetch Dry Run",
        },
        "safety": registry["safety"]
        | corpus["safety"]
        | {
            "production_records_written": False,
            "dashboard_contract_unchanged": True,
            "approved_api_metadata_only": True,
            "user_api_key_value_not_stored": True,
        },
        "hashes": {
            "api_registry_json": _sha256(registry_json),
            "strategy_research_corpus_json": _sha256(corpus_json),
        },
    }
    _write_reports(report, reports_dir)
    return report


def _write_reports(report: dict, reports_dir: Path) -> None:
    json_path = reports_dir / REPORT_JSON
    md_path = reports_dir / REPORT_MD
    marker_path = reports_dir / PASS_MARKER
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# V2.2-A External API Connector and Strategy Research Ingestion Acceptance",
                "",
                f"- status: {report['overall_status']}",
                f"- target: {report['acceptance_target']}",
                f"- run_id: {report['run_id']}",
                f"- api_registry_json: `{report['api_registry_json']}`",
                f"- strategy_research_corpus_json: `{report['strategy_research_corpus_json']}`",
                f"- connector_allow_count: `{report['summary']['connector_allow_count']}`",
                f"- connector_deny_count: `{report['summary']['connector_deny_count']}`",
                f"- research_record_count: `{report['summary']['research_record_count']}`",
                "- safety: no API key values, no broker API, no trading webhook, no raw research text",
                "",
            ]
        ),
        encoding="utf-8",
    )
    marker_path.write_text(
        "\n".join(
            [
                f"generated_at={report['generated_at']}",
                f"command={report.get('command') or ''}",
                "exit_code=0",
                "target=V2.2-A External API Connector and Strategy Research Ingestion",
                f"report_json={json_path}",
                f"report_json_sha256={_sha256(json_path)}",
                f"report_md={md_path}",
                f"report_md_sha256={_sha256(md_path)}",
                f"run_dir={report['run_dir']}",
                f"api_registry_json={report['api_registry_json']}",
                f"api_registry_json_sha256={report['hashes']['api_registry_json']}",
                f"strategy_research_corpus_json={report['strategy_research_corpus_json']}",
                f"strategy_research_corpus_json_sha256={report['hashes']['strategy_research_corpus_json']}",
                "network_used=false",
                "dashboard_contract_changed=false",
                "production_records_written=false",
                "no_secret_values_stored=true",
                "no_real_trade=true",
                "no_broker_api=true",
                "no_trading_webhook=true",
                "failed=0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fail_marker = reports_dir / FAIL_MARKER
    if fail_marker.exists():
        fail_marker.unlink()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])

    try:
        report = run_acceptance(
            output_root=args.output_root,
            reports_dir=args.reports_dir,
            run_id=args.run_id,
            command=command,
        )
    except Exception as exc:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        (args.reports_dir / FAIL_MARKER).write_text(
            "\n".join(
                [
                    f"generated_at={_now_iso()}",
                    f"command={command}",
                    "exit_code=1",
                    "target=V2.2-A External API Connector and Strategy Research Ingestion",
                    f"error={exc}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"V2.2-A External API Connector and Strategy Research Ingestion FAIL: {exc}")
        return 1

    print(
        "V2.2-A External API Connector and Strategy Research Ingestion PASS "
        f"run_id={report['run_id']} report={args.reports_dir / REPORT_JSON}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

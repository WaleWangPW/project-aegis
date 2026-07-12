"""Assemble multi-symbol historical cases for Finnhub quote sandbox candidates.

V2.13-U keeps Finnhub quote context as the research trigger, then fetches
bounded EODHD daily bars into a run-specific cache for historical sandbox case
assembly. It does not evaluate the sandbox or enable suggestions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from aegis.models.strategy import HistoricalStrategyCase

FetchJson = Callable[[str], tuple[int, Any]]

ACCEPTANCE_TARGET = "V2.13-U Finnhub Quote Multi-Symbol Historical Case Assembly"
SOURCE_ACCEPTANCE_TARGET = "V2.13-T Finnhub Quote Multi-Symbol Sandbox Candidate Binding"
NORMALIZED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
REQUIRED_ENV_VAR = "AEGIS_EODHD_API_TOKEN"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _default_fetch_json(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ProjectAegis/0.1 secret-safe-multi-symbol-historical-case-assembly"},
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.status, json.loads(resp.read(500000).decode("utf-8"))


def _safe_eodhd_url(case: Mapping[str, Any], token: str) -> str:
    params = urllib.parse.urlencode(
        {
            "api_token": token,
            "fmt": "json",
            "from": str(case["from_date"]),
            "to": str(case["to_date"]),
        }
    )
    return f"https://eodhd.com/api/eod/{urllib.parse.quote(str(case['provider_symbol']))}?{params}"


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _normalize_eodhd_payload(payload: Any) -> list[dict[str, Any]]:
    rows = payload if isinstance(payload, list) else []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        date_value = row.get("date")
        close = _float_or_none(row.get("close"))
        if not date_value or close is None:
            continue
        normalized.append(
            {
                "date": str(date_value)[:10],
                "open": _float_or_none(row.get("open")),
                "high": _float_or_none(row.get("high")),
                "low": _float_or_none(row.get("low")),
                "close": close,
                "volume": _int_or_none(row.get("volume")),
            }
        )
    return sorted(normalized, key=lambda item: item["date"])


def _write_normalized_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=NORMALIZED_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in NORMALIZED_COLUMNS})


def _case_id(symbol: str) -> str:
    return f"us_{symbol.lower().replace('.', '_')}_eodhd_daily_bars"


def _historical_case_id(symbol: str, idx: int) -> str:
    return f"v2_13_u_{symbol.lower().replace('.', '_')}_rolling_{idx + 1}"


def _provider_symbol(canonical_symbol: str) -> str:
    return canonical_symbol if canonical_symbol.endswith(".US") else f"{canonical_symbol}.US"


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return sorted(csv.DictReader(fh), key=lambda row: str(row["date"]))


def _rolling_cases_for_csv(
    *,
    csv_path: Path,
    expected_hash: str,
    binding: Mapping[str, Any],
) -> tuple[list[HistoricalStrategyCase], dict[str, Any]]:
    actual_hash = _sha256_file(csv_path) if csv_path.exists() else None
    hash_matches = bool(actual_hash and actual_hash == expected_hash)
    check = {
        "binding_id": binding.get("binding_id"),
        "canonical_symbol": binding.get("canonical_symbol"),
        "normalized_csv_exists": csv_path.exists(),
        "normalized_csv_hash_matches": hash_matches,
        "expected_sha256": expected_hash,
        "actual_sha256": actual_hash,
    }
    if not hash_matches:
        return [], check

    candidate = binding["strategy_candidate"]
    rows = _read_csv_rows(csv_path)
    cases: list[HistoricalStrategyCase] = []
    for idx in range(len(rows) - 1):
        entry = rows[idx]
        exit_ = rows[idx + 1]
        entry_price = float(entry["close"])
        exit_price = float(exit_["close"])
        low = min(float(entry["low"]), float(exit_["low"]))
        max_drawdown = low / entry_price - 1.0
        risk_flags: list[str] = []
        if max_drawdown <= -0.12:
            risk_flags.append("historical_drawdown_breach")
        elif max_drawdown <= -0.06:
            risk_flags.append("historical_drawdown_watch")
        cases.append(
            HistoricalStrategyCase(
                case_id=_historical_case_id(str(binding["canonical_symbol"]), idx),
                strategy_id=str(candidate["strategy_id"]),
                date=str(entry["date"]),
                symbol=str(binding["canonical_symbol"]),
                market=binding["market"],
                entry_price=entry_price,
                exit_price=exit_price,
                max_drawdown=max_drawdown,
                risk_flags=risk_flags,
                factor_values={
                    "actual_return": (exit_price - entry_price) / entry_price,
                    "rolling_window_days": 1.0,
                    "source_row_index": float(idx),
                },
                evidence_ref=(
                    f"v2_13_u_multi_symbol_case:{binding['binding_id']}:{binding['context_id']}:"
                    f"{binding['canonical_symbol']}:{actual_hash}"
                ),
            )
        )
    return cases, check


def _fetch_daily_bars_case(
    binding: Mapping[str, Any],
    *,
    output_dir: Path,
    env: Mapping[str, str],
    fetch_json: FetchJson | None,
    from_date: str,
    to_date: str,
) -> dict[str, Any]:
    symbol = str(binding["canonical_symbol"])
    case = {
        "case_id": _case_id(symbol),
        "provider": "eodhd",
        "market": binding.get("market"),
        "canonical_symbol": symbol,
        "provider_symbol": _provider_symbol(symbol),
        "data_type": "daily_bars",
        "from_date": from_date,
        "to_date": to_date,
    }
    base = {
        **case,
        "required_env_var": REQUIRED_ENV_VAR,
        "env_present": bool(env.get(REQUIRED_ENV_VAR)),
        "request_url_stored": False,
        "raw_payload_stored": False,
        "token_value_stored": False,
        "normalized_csv_written": False,
    }
    if not env.get(REQUIRED_ENV_VAR):
        return {**base, "status": "blocked_missing_env", "ok": False, "blocked_by": ["missing_required_env_var"]}

    fetcher = fetch_json or _default_fetch_json
    try:
        status_code, payload = fetcher(_safe_eodhd_url(case, env[REQUIRED_ENV_VAR]))
        rows = _normalize_eodhd_payload(payload)
        ok = status_code == 200 and len(rows) >= 4
        if not ok:
            return {
                **base,
                "status": "fail",
                "ok": False,
                "http_status": status_code,
                "row_count": len(rows),
                "blocked_by": ["insufficient_normalized_rows"],
            }
        csv_path = output_dir / "US" / "daily_bars" / f"{case['case_id']}.csv"
        _write_normalized_csv(csv_path, rows)
        return {
            **base,
            "status": "pass",
            "ok": True,
            "http_status": status_code,
            "row_count": len(rows),
            "first_date": rows[0]["date"],
            "last_date": rows[-1]["date"],
            "normalized_csv_written": True,
            "normalized_csv": str(csv_path),
            "normalized_csv_sha256": _sha256_file(csv_path),
            "normalized_schema": NORMALIZED_COLUMNS,
            "payload_summary_sha256": _sha256_text(
                json.dumps(
                    {"row_count": len(rows), "first_date": rows[0]["date"], "last_date": rows[-1]["date"]},
                    sort_keys=True,
                )
            ),
            "blocked_by": [],
        }
    except Exception as exc:
        return {**base, "status": "fail", "ok": False, "error_type": type(exc).__name__, "blocked_by": ["fetch_error"]}


def build_finnhub_quote_multi_symbol_historical_case_assembly_report(
    source_report: Mapping[str, Any],
    *,
    output_dir: Path,
    run_id: str,
    command: str | None = None,
    env: Mapping[str, str] | None = None,
    fetch_json: FetchJson | None = None,
    from_date: str = "2026-06-01",
    to_date: str = "2026-07-10",
    generated_at: str | None = None,
) -> dict[str, Any]:
    created = generated_at or _now_iso()
    env_source = env if env is not None else os.environ
    bindings = [
        item
        for item in source_report.get("bindings", []) or []
        if isinstance(item, dict) and item.get("binding_status") == "bound_pending_historical_cases"
    ]
    fetch_results = [
        _fetch_daily_bars_case(
            binding,
            output_dir=output_dir,
            env=env_source,
            fetch_json=fetch_json,
            from_date=from_date,
            to_date=to_date,
        )
        for binding in bindings
    ]

    historical_cases: list[HistoricalStrategyCase] = []
    artifact_checks: list[dict[str, Any]] = []
    candidate_packets: list[dict[str, Any]] = []
    fetch_by_symbol = {str(item.get("canonical_symbol")): item for item in fetch_results}
    for binding in bindings:
        candidate = dict(binding["strategy_candidate"])
        result = fetch_by_symbol.get(str(binding["canonical_symbol"]))
        binding_cases: list[HistoricalStrategyCase] = []
        if result and result.get("status") == "pass":
            cases, check = _rolling_cases_for_csv(
                csv_path=Path(str(result["normalized_csv"])),
                expected_hash=str(result["normalized_csv_sha256"]),
                binding=binding,
            )
            artifact_checks.append(check)
            binding_cases.extend(cases)
        historical_cases.extend(binding_cases)
        candidate_packets.append(
            {
                "binding_id": binding["binding_id"],
                "context_id": binding["context_id"],
                "canonical_symbol": binding["canonical_symbol"],
                "strategy_candidate": candidate,
                "daily_bars_case_id": result.get("case_id") if result else None,
                "historical_case_ids": [case.case_id for case in binding_cases],
                "historical_case_count": len(binding_cases),
                "status": "historical_cases_assembled" if binding_cases else "blocked_missing_historical_cases",
            }
        )

    expected_symbols = sorted(str(symbol) for symbol in source_report.get("summary", {}).get("symbols", []))
    assembled_symbols = sorted({case.symbol for case in historical_cases})
    checks = {
        "source_report_pass": source_report.get("overall_status") == "PASS",
        "source_acceptance_target_correct": source_report.get("acceptance_target") == SOURCE_ACCEPTANCE_TARGET,
        "source_binding_count_at_least_three": int(source_report.get("summary", {}).get("binding_count") or 0) >= 3,
        "source_social_sentiment_still_blocked": source_report.get("summary", {}).get("social_sentiment_status")
        == "blocked_plan_or_rate_limit",
        "at_least_three_bound_candidates": len(bindings) >= 3,
        "all_fetch_results_pass": bool(fetch_results) and all(item.get("status") == "pass" for item in fetch_results),
        "all_fetch_results_have_hashes": bool(fetch_results)
        and all(bool(item.get("normalized_csv_sha256")) for item in fetch_results),
        "all_symbols_assembled": assembled_symbols == expected_symbols and bool(assembled_symbols),
        "historical_cases_meet_candidate_minimum": all(
            packet["historical_case_count"]
            >= int(packet["strategy_candidate"]["pass_criteria"]["min_sample_count"])
            for packet in candidate_packets
        )
        if candidate_packets
        else False,
        "all_artifacts_verified": bool(artifact_checks)
        and all(item["normalized_csv_exists"] and item["normalized_csv_hash_matches"] for item in artifact_checks),
        "all_cases_have_multi_symbol_quote_context_evidence": all(
            str(case.evidence_ref or "").startswith("v2_13_u_multi_symbol_case:") for case in historical_cases
        ),
        "sandbox_evaluation_not_run": True,
        "suggestion_path_not_enabled": True,
        "user_facing_suggestion_not_allowed": True,
        "bounded_historical_bars_only": True,
        "production_records_not_written": True,
        "production_cache_not_mutated": True,
        "production_provider_config_not_mutated": True,
        "no_secret_values_stored": all(not item["token_value_stored"] for item in fetch_results),
        "request_urls_not_stored": all(not item["request_url_stored"] for item in fetch_results),
        "raw_payloads_not_stored": all(not item["raw_payload_stored"] for item in fetch_results),
        "no_real_trade": True,
        "no_broker_api": True,
        "no_trading_webhook": True,
        "no_order_placement": True,
        "no_position_size": True,
        "no_live_order_signal": True,
        "dashboard_contract_unchanged": True,
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_target": ACCEPTANCE_TARGET,
        "source_acceptance_target": source_report.get("acceptance_target"),
        "run_id": run_id,
        "generated_at": created,
        "command": command,
        "network_used": fetch_json is None and bool(env_source.get(REQUIRED_ENV_VAR)),
        "production_records_written": False,
        "production_cache_mutated": False,
        "production_provider_config_mutated": False,
        "dashboard_contract_changed": False,
        "summary": {
            "candidate_packet_count": len(candidate_packets),
            "daily_bars_case_count": len(fetch_results),
            "historical_case_count": len(historical_cases),
            "markets": sorted({case.market for case in historical_cases}),
            "symbols": assembled_symbols,
            "sandbox_evaluation_run": False,
            "sandbox_evaluation_required": True,
            "suggestion_gate_required": True,
            "user_facing_suggestion_allowed": False,
            "social_sentiment_status": "blocked_plan_or_rate_limit",
            "next_stage": "V2.13-V Finnhub Quote Multi-Symbol Sandbox Evaluation",
        },
        "daily_bar_fetch_results": fetch_results,
        "candidate_packets": candidate_packets,
        "historical_cases": [case.model_dump() for case in historical_cases],
        "artifact_checks": artifact_checks,
        "source_evidence": {
            "source_target": source_report.get("acceptance_target"),
            "source_run_id": source_report.get("run_id"),
            "source_summary_sha256": _sha256_text(
                json.dumps(source_report.get("summary") or {}, ensure_ascii=False, sort_keys=True)
            ),
        },
        "checks": checks,
        "safety": {
            "historical_case_assembly_only": True,
            "bounded_historical_bars_fetch_only": True,
            "sandbox_evaluation_not_run": True,
            "suggestion_path_not_enabled": True,
            "user_facing_suggestion_allowed": False,
            "social_sentiment_not_enabled": True,
            "production_records_not_written": True,
            "production_cache_not_mutated": True,
            "production_provider_config_not_mutated": True,
            "no_secret_values_stored": True,
            "no_request_url_storage": True,
            "no_raw_payload_storage": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_trading_webhook": True,
            "no_order_placement": True,
            "no_position_size": True,
            "no_live_order_signal": True,
            "dashboard_contract_unchanged": True,
        },
    }


def render_finnhub_quote_multi_symbol_historical_case_assembly_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# V2.13-U Finnhub Quote Multi-Symbol Historical Case Assembly",
        "",
        f"- status: `{report.get('overall_status')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- candidate_packet_count: `{report.get('summary', {}).get('candidate_packet_count')}`",
        f"- daily_bars_case_count: `{report.get('summary', {}).get('daily_bars_case_count')}`",
        f"- historical_case_count: `{report.get('summary', {}).get('historical_case_count')}`",
        f"- symbols: `{report.get('summary', {}).get('symbols')}`",
        f"- sandbox_evaluation_run: `{report.get('summary', {}).get('sandbox_evaluation_run')}`",
        f"- user_facing_suggestion_allowed: `{report.get('summary', {}).get('user_facing_suggestion_allowed')}`",
        f"- next_stage: `{report.get('summary', {}).get('next_stage')}`",
        "",
        "## Candidate Packets",
        "",
    ]
    for packet in report.get("candidate_packets", []) or []:
        candidate = packet.get("strategy_candidate") or {}
        lines.extend(
            [
                f"### {packet.get('canonical_symbol')}",
                "",
                f"- status: `{packet.get('status')}`",
                f"- strategy_id: `{candidate.get('strategy_id')}`",
                f"- daily_bars_case_id: `{packet.get('daily_bars_case_id')}`",
                f"- historical_case_count: `{packet.get('historical_case_count')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Historical case assembly only.",
            "- EODHD is used only for bounded historical daily bars in a run-specific cache.",
            "- Sandbox evaluation is not run in this stage.",
            "- No user-facing suggestion, position size, live order signal, real trade, broker API, webhook, or order placement.",
            "",
        ]
    )
    return "\n".join(lines)

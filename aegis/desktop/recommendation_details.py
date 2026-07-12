"""aegis/desktop/recommendation_details.py — Recommendation Details Mirror builder.

Builds:
    data/desktop/recommendation_details.json

Reads only:
    data/records/recommendations.jsonl
    data/records/decisions.jsonl
    data/records/expert_opinions.jsonl
    data/records/data_gaps.jsonl
    data/records/signals.jsonl

Strict non-goals:
- Does NOT modify Decision Engine thresholds
- Does NOT force Action / Ready / Watch / Exit
- Does NOT change Expert Agent opinions
- Does NOT fabricate recommendation outcomes
- Does NOT create PaperTrade
- Does NOT connect broker
- Does NOT modify dashboard/index.html
- Does NOT add composite scoring
- Does NOT read, print, or expose .env or any token
- Does NOT special-case CRCL
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECORDS_DIR = REPO_ROOT / "data" / "records"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "desktop" / "recommendation_details.json"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_SESSION_ORDER: dict[str, int] = {"pre_market": 0, "midday": 1, "close": 2}

_BAR_SIGNAL_NAMES = (
    "trend_ma_alignment",
    "relative_strength_vs_index",
    "volume_expansion",
    "risk_volatility_drawdown",
)

_STALE_DAILY_BAR_HINTS = (
    "no daily bars returned",
    "yfinance package is not installed",
    "dependency_missing",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                records.append(obj)
    return records


def _parse_dt(ts: Optional[str]) -> datetime:
    if not ts:
        return _EPOCH
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return _EPOCH


def _normalize_date(date_str: str) -> str:
    if date_str and len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str


def _compute_latest_flags(raw_recs: list[dict[str, Any]]) -> tuple[set[int], set[int]]:
    best_rec_id: dict[str, tuple] = {}
    for pos, rec in enumerate(raw_recs):
        rec_id = rec.get("recommendation_id")
        if rec_id is None:
            continue
        key = (_parse_dt(rec.get("created_at")), pos)
        if rec_id not in best_rec_id or key > best_rec_id[rec_id]:
            best_rec_id[rec_id] = key

    latest_for_rec_id_indices: set[int] = set()
    for pos, rec in enumerate(raw_recs):
        rec_id = rec.get("recommendation_id")
        if rec_id is None:
            continue
        if (_parse_dt(rec.get("created_at")), pos) == best_rec_id.get(rec_id):
            latest_for_rec_id_indices.add(pos)

    best_symbol: dict[str, tuple] = {}
    for pos in latest_for_rec_id_indices:
        rec = raw_recs[pos]
        sym = rec.get("symbol")
        if sym is None:
            continue
        key = (
            rec.get("date", ""),
            _SESSION_ORDER.get(rec.get("session", ""), 99),
            _parse_dt(rec.get("created_at")),
            pos,
        )
        if sym not in best_symbol or key > best_symbol[sym]:
            best_symbol[sym] = key

    latest_for_symbol_indices: set[int] = set()
    for pos in latest_for_rec_id_indices:
        rec = raw_recs[pos]
        sym = rec.get("symbol")
        if sym is None:
            continue
        key = (
            rec.get("date", ""),
            _SESSION_ORDER.get(rec.get("session", ""), 99),
            _parse_dt(rec.get("created_at")),
            pos,
        )
        if key == best_symbol.get(sym):
            latest_for_symbol_indices.add(pos)

    return latest_for_rec_id_indices, latest_for_symbol_indices


def _find_decision(raw_decs: list[dict[str, Any]], recommendation_id: str, created_at: str) -> dict[str, Any]:
    candidates = [
        d for d in raw_decs
        if d.get("recommendation_id") == recommendation_id
        or d.get("decision_id") == recommendation_id
    ]
    if not candidates:
        return {}
    exact = [d for d in candidates if d.get("created_at") == created_at]
    if exact:
        return max(exact, key=lambda d: (_parse_dt(d.get("created_at")), 0))
    target_dt = _parse_dt(created_at)
    return min(
        candidates,
        key=lambda d: abs((_parse_dt(d.get("created_at")) - target_dt).total_seconds()),
    )


def _find_opinions(raw_ops: list[dict[str, Any]], recommendation_id: str, created_at: str) -> list[dict[str, Any]]:
    candidates = [o for o in raw_ops if o.get("recommendation_id") == recommendation_id]
    if not candidates:
        return []
    exact = [o for o in candidates if o.get("created_at") == created_at]
    if exact:
        return exact
    target_dt = _parse_dt(created_at)
    best_delta = min(
        abs((_parse_dt(o.get("created_at")) - target_dt).total_seconds())
        for o in candidates
    )
    return [
        o for o in candidates
        if abs((_parse_dt(o.get("created_at")) - target_dt).total_seconds()) <= best_delta + 1.0
    ]


def _gaps_for_rec(
    raw_gaps: list[dict[str, Any]],
    symbol: Optional[str],
    date: Optional[str],
    market: Optional[str] = None,
) -> list[str]:
    if not date:
        return []
    rec_date_norm = _normalize_date(date)
    notes: list[str] = []
    seen: set[str] = set()

    for gap in raw_gaps:
        gap_sym = gap.get("symbol")
        if gap_sym is not None:
            if gap_sym != symbol:
                continue
        else:
            if market is not None and gap.get("market") != market:
                continue

        if _normalize_date(gap.get("date", "")) != rec_date_norm:
            continue

        msg = gap.get("message", "")
        if msg and msg not in seen:
            notes.append(msg)
            seen.add(msg)

    return notes


def _latest_signal(
    raw_signals: list[dict[str, Any]],
    *,
    symbol: Optional[str],
    market: Optional[str],
    date: Optional[str],
    signal_name: str,
) -> dict[str, Any] | None:
    if not symbol:
        return None

    rows: list[dict[str, Any]] = []
    date_norm = _normalize_date(date or "")

    for sig in raw_signals:
        if sig.get("symbol") != symbol:
            continue
        if market is not None and sig.get("market") != market:
            continue
        if sig.get("signal_name") != signal_name:
            continue
        if date_norm and _normalize_date(sig.get("date", "")) != date_norm:
            continue
        if not isinstance(sig.get("value"), dict):
            continue
        rows.append(sig)

    return rows[-1] if rows else None


def _latest_bar_signals(
    raw_signals: list[dict[str, Any]],
    *,
    symbol: Optional[str],
    market: Optional[str],
    date: Optional[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in _BAR_SIGNAL_NAMES:
        sig = _latest_signal(raw_signals, symbol=symbol, market=market, date=date, signal_name=name)
        if sig:
            result[name] = sig
    return result


def _classify_data_quality_notes(
    notes: list[str],
    *,
    has_bar_signal_values: bool,
) -> tuple[list[str], list[dict[str, str]]]:
    current: list[str] = []
    superseded: list[dict[str, str]] = []

    for note in notes:
        low = note.lower()
        should_supersede = has_bar_signal_values and any(h in low for h in _STALE_DAILY_BAR_HINTS)
        if should_supersede:
            superseded.append(
                {
                    "message": note,
                    "status": "superseded",
                    "reason": "later bar-derived signal evidence exists for this recommendation",
                }
            )
        else:
            current.append(note)

    return current, superseded


def _build_data_availability(
    *,
    signals_by_name: dict[str, dict[str, Any]],
    expert_opinions: list[dict[str, Any]],
) -> dict[str, Any]:
    signals_with_data = [
        f"signal:{sig.get('signal_id')}"
        for sig in signals_by_name.values()
        if sig.get("signal_id")
    ]

    signals_with_numeric_values = [
        name
        for name, sig in signals_by_name.items()
        if isinstance(sig.get("value"), dict)
    ]

    missing = sorted({
        str(item)
        for op in expert_opinions
        for item in (op.get("missing_data") or [])
    })

    return {
        "bars_available": bool(signals_with_numeric_values),
        "bars_used_count": None,
        "signals_with_data": signals_with_data,
        "signals_with_numeric_values": signals_with_numeric_values,
        "signals_missing": missing,
        "note": "bars_used_count is null because raw bar count is not stored in current recommendation records",
    }


def _build_risk_veto_details(
    *,
    rec: dict[str, Any],
    decision_record: dict[str, Any],
    expert_opinions: list[dict[str, Any]],
    signals_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    risk_signal = signals_by_name.get("risk_volatility_drawdown")
    volume_signal = signals_by_name.get("volume_expansion")
    trend_signal = signals_by_name.get("trend_ma_alignment")
    rs_signal = signals_by_name.get("relative_strength_vs_index")

    risk_v = risk_signal.get("value", {}) if risk_signal else {}
    volume_v = volume_signal.get("value", {}) if volume_signal else {}
    trend_v = trend_signal.get("value", {}) if trend_signal else {}
    rs_v = rs_signal.get("value", {}) if rs_signal else {}

    risk_flags: list[str] = []
    for flag in rec.get("risks") or []:
        if flag not in risk_flags:
            risk_flags.append(flag)

    for op in expert_opinions:
        if op.get("expert_name") == "RiskAgent":
            for flag in op.get("risks") or []:
                if flag not in risk_flags:
                    risk_flags.append(flag)

    for flag in risk_v.get("flags", []) if isinstance(risk_v.get("flags"), list) else []:
        if flag not in risk_flags:
            risk_flags.append(flag)

    source_signal_ids = []
    if risk_signal and risk_signal.get("signal_id"):
        source_signal_ids.append(f"signal:{risk_signal.get('signal_id')}")

    metrics = {
        "volatility": risk_v.get("volatility"),
        "max_drawdown": risk_v.get("max_drawdown"),
        "latest_volume": volume_v.get("latest_vol"),
        "avg_volume": volume_v.get("avg_vol"),
        "avg_dollar_volume": None,
        "recent_return": trend_v.get("recent_return"),
        "symbol_return_5d": rs_v.get("symbol_return"),
        "index_return_5d": rs_v.get("index_return"),
        "relative_strength_5d": rs_v.get("relative_strength"),
    }

    source_signal_values = {
        "risk_volatility_drawdown": risk_v or None,
        "volume_expansion": volume_v or None,
        "trend_ma_alignment": trend_v or None,
        "relative_strength_vs_index": rs_v or None,
    }

    return {
        "risk_veto_triggered": bool(decision_record.get("risk_veto_triggered")),
        "risk_flags": risk_flags,
        "source_signal_ids": source_signal_ids,
        "metrics": metrics,
        "source_signal_values": source_signal_values,
        "metrics_generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "notes": [
            "Metrics are copied from latest matching Signal.value records.",
            "avg_dollar_volume is null because price*volume liquidity metric is not recorded yet.",
        ],
    }


def build_recommendation_details(
    records_dir: Path = DEFAULT_RECORDS_DIR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    raw_recs = _read_jsonl(records_dir / "recommendations.jsonl")
    raw_decs = _read_jsonl(records_dir / "decisions.jsonl")
    raw_ops = _read_jsonl(records_dir / "expert_opinions.jsonl")
    raw_gaps = _read_jsonl(records_dir / "data_gaps.jsonl")
    raw_signals = _read_jsonl(records_dir / "signals.jsonl")

    latest_for_rec_id_indices, latest_for_symbol_indices = _compute_latest_flags(raw_recs)

    output_recs: list[dict[str, Any]] = []

    for pos, rec in enumerate(raw_recs):
        rec_id = rec.get("recommendation_id")
        if rec_id is None:
            continue

        sym = rec.get("symbol")
        market = rec.get("market")
        date = rec.get("date")
        rec_created_at = rec.get("created_at", "")

        dec = _find_decision(raw_decs, rec_id, rec_created_at)
        decision_record: dict[str, Any] = {
            "decision_id": dec.get("decision_id"),
            "risk_veto_triggered": dec.get("risk_veto_triggered", False),
            "risk_veto_reason": dec.get("risk_veto_reason"),
            "support_count": dec.get("support_count", 0),
            "oppose_count": dec.get("oppose_count", 0),
            "neutral_count": dec.get("neutral_count", 0),
            "veto_count": dec.get("veto_count", 0),
        }

        expert_opinions: list[dict[str, Any]] = []
        for op in _find_opinions(raw_ops, rec_id, rec_created_at):
            expert_opinions.append(
                {
                    "expert_name": op.get("expert_name"),
                    "stance": op.get("stance"),
                    "confidence": op.get("confidence"),
                    "summary": op.get("summary"),
                    "evidence": op.get("evidence") or [],
                    "risks": op.get("risks") or [],
                    "missing_data": op.get("missing_data") or [],
                }
            )

        signals_by_name = _latest_bar_signals(
            raw_signals,
            symbol=sym,
            market=market,
            date=date,
        )

        raw_notes = _gaps_for_rec(raw_gaps, sym, date, market)
        data_quality_notes, historical_or_superseded = _classify_data_quality_notes(
            raw_notes,
            has_bar_signal_values=bool(signals_by_name),
        )

        data_availability = _build_data_availability(
            signals_by_name=signals_by_name,
            expert_opinions=expert_opinions,
        )

        risk_veto_details = _build_risk_veto_details(
            rec=rec,
            decision_record=decision_record,
            expert_opinions=expert_opinions,
            signals_by_name=signals_by_name,
        )

        output_recs.append(
            {
                "recommendation_id": rec_id,
                "record_index": pos,
                "is_latest_for_recommendation_id": pos in latest_for_rec_id_indices,
                "is_latest_for_symbol": pos in latest_for_symbol_indices,
                "date": date,
                "session": rec.get("session"),
                "symbol": sym,
                "name": rec.get("name"),
                "market": market,
                "status": rec.get("status"),
                "action_label": rec.get("action_label"),
                "confidence": rec.get("confidence"),
                "decision_summary": rec.get("decision_summary"),
                "support_reasons": rec.get("support_reasons") or [],
                "oppose_reasons": rec.get("oppose_reasons") or [],
                "risks": rec.get("risks") or [],
                "invalidation_conditions": rec.get("invalidation_conditions") or [],
                "why_not_action": dec.get("why_not_action"),
                "decision_record": decision_record,
                "expert_opinions": expert_opinions,
                "data_quality_notes": data_quality_notes,
                "historical_or_superseded_data_quality_notes": historical_or_superseded,
                "data_availability": data_availability,
                "risk_veto_details": risk_veto_details,
            }
        )

    latest_recs = [r for r in output_recs if r.get("is_latest_for_symbol")]

    if not latest_recs and output_recs:
        latest_recs = [output_recs[-1]]
        latest_recs[0]["is_latest_for_recommendation_id"] = True
        latest_recs[0]["is_latest_for_symbol"] = True

    latest_status_counts: dict[str, int] = {"Action": 0, "Ready": 0, "Watch": 0, "Exit": 0}
    for r in latest_recs:
        st = r.get("status") or ""
        if st in latest_status_counts:
            latest_status_counts[st] += 1

    unique_rec_ids = len(set(
        r.get("recommendation_id") for r in raw_recs if r.get("recommendation_id")
    ))

    output: dict[str, Any] = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "source_files": {
            "recommendations": "data/records/recommendations.jsonl",
            "decisions": "data/records/decisions.jsonl",
            "expert_opinions": "data/records/expert_opinions.jsonl",
            "data_gaps": "data/records/data_gaps.jsonl",
            "signals": "data/records/signals.jsonl",
        },
        "summary": {
            "total_records": len(raw_recs),
            "unique_recommendation_ids": unique_rec_ids,
            "latest_per_symbol_count": len(latest_recs),
            "historical_record_count": len(raw_recs) - len(latest_recs),
            "latest_status_counts": latest_status_counts,
            "status_counts": latest_status_counts,
        },
        "latest_recommendations": latest_recs,
        "recommendations": output_recs,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output


if __name__ == "__main__":
    import sys

    result = build_recommendation_details()
    summary = result["summary"]
    print(
        f"recommendation_details.json written — "
        f"total_records={summary['total_records']}, "
        f"unique_ids={summary['unique_recommendation_ids']}, "
        f"latest_per_symbol={summary['latest_per_symbol_count']}, "
        f"latest_status={summary['latest_status_counts']}"
    )
    sys.exit(0)

"""DashboardBuilder — Phase 5 §9.2, extended by Phase 6 §5.9.

Reads existing MarketSnapshot/RecommendationRecord/PaperTrade/ReviewRecord
JSONL records plus `config/holdings.yaml` and produces a validated Dashboard
JSON payload. Never fabricates a recommendation, price, return, or review
summary — missing source data becomes an explicit `DATA_GAP` string or an
honest fallback sentence, never a guess. Still never touches
`dashboard/index.html`; still no new schema fields beyond what Dashboard v1
already renders (`paper_trading.new_today`/`open_positions_perf` are only
counted by the UI, never rendered item-by-item — see `dashboard/index.html`
`renderPaperTrading()`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import yaml

from aegis.dashboard.schema import validate_dashboard_payload
from aegis.models.holding import Holding
from aegis.utils.jsonl import read_jsonl

_MARKET_LABELS = {"A": "A 股", "H": "H 股", "US": "美股"}
_STATUS_TO_HOLDING_ACTION = {"Exit": "exit", "Action": "action", "Ready": "ready", "Watch": "wait"}
_STATUS_TO_BUCKET = {"Action": "action", "Ready": "ready", "Watch": "watch"}

_NO_SUPPORT_TEXT = "暂无明确支持理由"
_NO_OPPOSE_TEXT = "暂无明确反对理由"
_NO_RISK_TEXT = "暂无明确风险记录"
_NO_INVALIDATION_TEXT = "暂无失效条件记录"
_NO_SECTOR_TEXT = "未知行业"
_NO_ACTION_LABEL_TEXT = "持有观察"
_NO_REVIEW_TEXT = "尚无复盘记录"


def _first_non_empty(values: Optional[list], fallback: str) -> str:
    for value in values or []:
        if value:
            return value
    return fallback


class DashboardBuilder:
    def __init__(
        self,
        records_dir: Path,
        holdings_config_path: Path,
        output_path: Path,
        config: Optional[dict] = None,
    ):
        self.records_dir = Path(records_dir)
        self.holdings_config_path = Path(holdings_config_path)
        self.output_path = Path(output_path)
        self.config = config or {}

    def build(self, date: str, session: str = "pre_market") -> dict:
        market_snapshots = self._load_market_snapshots(date, session)
        recommendations = self._load_recommendations(date, session)
        holdings = self._load_holdings()
        latest_rec_by_holding = self._latest_recommendation_by_symbol(recommendations)
        paper_trades = self._load_paper_trades()
        reviews = self._load_reviews()

        payload = {
            "date": date,
            "stage_note": "Phase 6 · Paper Trading + Review 后端已接入",
            "market_snapshot": self._build_market_snapshot_section(market_snapshots),
            "today_focus": self._build_today_focus(recommendations, holdings),
            "holdings": [
                self._map_holding(h, latest_rec_by_holding.get((h.market, h.symbol))) for h in holdings
            ],
            "recommendations": self._build_recommendation_buckets(recommendations),
            "paper_trading": self._build_paper_trading_section(paper_trades, date),
            "review_note": self._build_review_note(reviews),
        }
        return validate_dashboard_payload(payload)

    def write_json(self, payload: dict) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.output_path

    # -- internals -----------------------------------------------------

    def _load_market_snapshots(self, date: str, session: str) -> dict[str, dict]:
        matches: dict[str, dict] = {}
        for row in read_jsonl(self.records_dir / "market_snapshots.jsonl"):
            if row.get("date") == date and row.get("session") == session and row.get("market") in _MARKET_LABELS:
                matches[row["market"]] = row  # append-only file, last write wins
        return matches

    def _load_recommendations(self, date: str, session: str) -> list[dict]:
        return [
            row
            for row in read_jsonl(self.records_dir / "recommendations.jsonl")
            if row.get("date") == date and row.get("session") == session
        ]

    def _load_holdings(self) -> list[Holding]:
        if not self.holdings_config_path.exists():
            return []
        with self.holdings_config_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return [Holding(**item) for item in raw.get("holdings", [])]

    def _latest_recommendation_by_symbol(self, recommendations: list[dict]) -> dict[tuple, dict]:
        latest: dict[tuple, dict] = {}
        for row in recommendations:
            latest[(row.get("market"), row.get("symbol"))] = row  # last one for this date/session wins
        return latest

    def _build_market_snapshot_section(self, market_snapshots: dict[str, dict]) -> dict:
        section = {}
        for market, label in _MARKET_LABELS.items():
            snap = market_snapshots.get(market)
            if snap is None:
                section[market] = f"DATA_GAP: 未找到 {label} MarketSnapshot"
            else:
                summary = snap.get("summary") or f"DATA_GAP: {label} MarketSnapshot 缺少 summary"
                section[market] = f"{label}：{summary}"
        return section

    def _build_recommendation_buckets(self, recommendations: list[dict]) -> dict:
        buckets: dict[str, list] = {"action": [], "ready": [], "watch": []}
        for row in recommendations:
            bucket_key = _STATUS_TO_BUCKET.get(row.get("status"))
            if bucket_key is None:
                continue  # Exit (or any unrecognized status) is not put in a bucket
            buckets[bucket_key].append(self._map_recommendation_item(row))
        return buckets

    def _map_recommendation_item(self, row: dict) -> dict:
        return {
            "ticker": row.get("symbol"),
            "market": row.get("market"),
            "industry": row.get("sector") or _NO_SECTOR_TEXT,
            "reason": _first_non_empty(row.get("support_reasons"), row.get("decision_summary") or _NO_SUPPORT_TEXT),
            "counter_reason": _first_non_empty(row.get("oppose_reasons"), _NO_OPPOSE_TEXT),
            "risk": _first_non_empty(row.get("risks"), _NO_RISK_TEXT),
            "invalidation_condition": _first_non_empty(row.get("invalidation_conditions"), _NO_INVALIDATION_TEXT),
        }

    def _map_holding(self, holding: Holding, latest_rec: Optional[dict]) -> dict:
        if latest_rec is None:
            return {
                "ticker": holding.symbol,
                "market": holding.market,
                "shares": holding.shares,
                "cost_price": holding.avg_cost,
                "action": "wait",
                "action_label": _NO_ACTION_LABEL_TEXT,
                "reason": "尚无该持仓的 RecommendationRecord，Decision Engine 尚未对其给出判断。",
                "risk": _NO_RISK_TEXT,
                "invalidation_condition": _NO_INVALIDATION_TEXT,
            }

        return {
            "ticker": holding.symbol,
            "market": holding.market,
            "shares": holding.shares,
            "cost_price": holding.avg_cost,
            "action": _STATUS_TO_HOLDING_ACTION.get(latest_rec.get("status"), "wait"),
            "action_label": latest_rec.get("action_label") or _NO_ACTION_LABEL_TEXT,
            "reason": latest_rec.get("decision_summary") or "暂无决策摘要",
            "risk": _first_non_empty(latest_rec.get("risks"), _NO_RISK_TEXT),
            "invalidation_condition": _first_non_empty(latest_rec.get("invalidation_conditions"), _NO_INVALIDATION_TEXT),
        }

    def _build_today_focus(self, recommendations: list[dict], holdings: list[Holding]) -> list[dict]:
        focus: list[dict] = []

        for row in recommendations:
            if row.get("status") == "Exit":
                focus.append(
                    {
                        "type": "持仓变化",
                        "text": (
                            f"{row.get('symbol')}（{row.get('market')}）触发 Exit："
                            f"{row.get('decision_summary') or '详见对应 RecommendationRecord'}"
                        ),
                    }
                )

        if not focus and holdings:
            symbols = ", ".join(h.symbol for h in holdings)
            focus.append({"type": "系统状态", "text": f"当前持仓（{symbols}）本次未触发 Exit。"})

        if not recommendations:
            focus.append(
                {"type": "系统状态", "text": "DATA_GAP: 本次请求的 date/session 未找到 RecommendationRecord。"}
            )

        return focus

    # -- Phase 6: paper trading / review --------------------------------

    def _load_paper_trades(self) -> list[dict]:
        return list(read_jsonl(self.records_dir / "paper_trades.jsonl"))

    def _load_reviews(self) -> list[dict]:
        return list(read_jsonl(self.records_dir / "reviews.jsonl"))

    def _build_paper_trading_section(self, paper_trades: list[dict], date: str) -> dict:
        """Only ever reads persisted `PaperTrade` rows — never re-computes
        a return/drawdown here (that is `PaperTradeService`'s job). Empty
        state stays honest (`[]`, not a placeholder trade)."""
        new_today = [t for t in paper_trades if t.get("entry_date") == date]
        open_positions = [t for t in paper_trades if t.get("status") == "open"]
        return {
            "new_today": [self._map_paper_trade(t) for t in new_today],
            "open_positions_perf": [self._map_paper_trade(t) for t in open_positions],
        }

    def _map_paper_trade(self, trade: dict) -> dict:
        return {
            "ticker": trade.get("symbol"),
            "market": trade.get("market"),
            "entry_date": trade.get("entry_date"),
            "entry_price": trade.get("entry_price"),
            "status": trade.get("status"),
            "return_5d": trade.get("return_5d"),
            "return_10d": trade.get("return_10d"),
            "return_20d": trade.get("return_20d"),
            "return_40d": trade.get("return_40d"),
            "max_drawdown": trade.get("max_drawdown"),
        }

    def _build_review_note(self, reviews: list[dict]) -> str:
        if not reviews:
            return _NO_REVIEW_TEXT

        resolved = [r for r in reviews if r.get("outcome") in ("success", "failure", "mixed")]
        success_count = sum(1 for r in resolved if r.get("outcome") == "success")
        failure_count = sum(1 for r in resolved if r.get("outcome") == "failure")
        mixed_count = sum(1 for r in resolved if r.get("outcome") == "mixed")
        pending_count = len(reviews) - len(resolved)

        parts = [f"共 {len(reviews)} 条复盘记录"]
        if resolved:
            parts.append(f"成功 {success_count} 笔、失败 {failure_count} 笔、其他 {mixed_count} 笔")
        if pending_count:
            parts.append(f"另有 {pending_count} 笔数据不足暂无法判定（inconclusive）")
        return "，".join(parts) + "。"

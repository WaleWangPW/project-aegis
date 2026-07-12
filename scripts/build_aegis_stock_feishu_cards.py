#!/usr/bin/env python3
"""Build Feishu interactive cards for the OpenClaw stock assistant.

The card values are designed to be routed back to Aegis by
handle_aegis_stock_card_action.py. This file does not send messages and does
not read secrets.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data" / "reports"
WORKBENCH = REPORTS / "stock_selection_workbench_latest.json"
OUTPUT = REPORTS / "aegis_stock_assistant_feishu_cards_latest.json"
PRESENTATION_OUTPUT = REPORTS / "aegis_stock_assistant_feishu_presentations_latest.json"
OUTPUT_REPORT = REPORTS / "aegis_stock_assistant_feishu_cards_latest_report.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _md(text: str) -> dict[str, str]:
    return {"tag": "lark_md", "content": text}


def _button(label: str, action: str, item: dict[str, Any], button_type: str = "default") -> dict[str, Any]:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": button_type,
        "value": {
            "system": "project_aegis",
            "source": "openclaw_stock_assistant",
            "action": action,
            "symbol": item.get("symbol"),
            "name": item.get("name"),
            "market": item.get("market"),
            "status": item.get("status"),
            "score": item.get("score"),
            "record_mode": "feedback_evidence_only",
            "real_trade_allowed": False,
        },
    }


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:+.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_price(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _short(text: Any, limit: int = 150) -> str:
    text = str(text or "").strip()
    if not text:
        return "暂无可靠简介"
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _compact_name(item: dict[str, Any]) -> str:
    name = str(item.get("name") or "").strip()
    if item.get("market") == "US":
        for suffix in [" Incorporated", ", Inc.", " Inc.", " Corporation", " Corp."]:
            name = name.replace(suffix, "")
    return name


def _company_profile(item: dict[str, Any]) -> str:
    desc = item.get("industry_or_description") or ""
    market = item.get("market")
    if market == "A":
        return f"{_compact_name(item)}：{_short(desc, 34)}"
    return _short(str(desc).replace(" · ", "："), 72)


def _plain_news_title(title: str) -> str:
    replacements = {
        "Bets $10 Billion on": "拟以约100亿美元押注/收购",
        "doubles down on": "上调/重申看好",
        "stock target": "目标价",
        "Boosts": "提振",
        "Shares": "股价",
        "Tightens": "收紧",
        "Strategy": "策略",
        "Amid Rising": "在上升的",
        "Concerns": "担忧中",
        "Among": "列入",
        "Earnings Picks": "财报季关注名单",
    }
    text = title
    for old, new in replacements.items():
        text = text.replace(old, new)
    return _short(text, 88)


def _signal_news_summary(item: dict[str, Any]) -> str:
    matches = [str(x) for x in (item.get("strategy_matches") or [])]
    signal_bits = [
        x
        for x in matches
        if any(key in x for key in ["新闻", "机构调研", "高管增持", "主业贡献", "现金流", "毛利率", "ROE"])
    ][:3]
    if signal_bits:
        return "系统信号摘要：" + "；".join(signal_bits)
    return "暂无可靠公司新闻摘要；需要继续补公告/新闻后再决定。"


def _news_lines(item: dict[str, Any], limit: int = 2) -> list[str]:
    news = item.get("news_items") or []
    lines = []
    for n in news[:limit]:
        title = n.get("title") or "公司动态"
        date = (n.get("date") or "")[:10]
        prefix = f"{date} " if date else ""
        summary = (n.get("display_summary") or n.get("summary") or "").strip()
        text = _short(summary, 92) if summary else _plain_news_title(title)
        lines.append(f"- {prefix}{text}")
    if not lines:
        summary = item.get("news_summary")
        if summary and "未找到" not in summary and "未进入" not in summary:
            lines.append(f"- {_plain_news_title(summary)}")
        else:
            lines.append(f"- {_signal_news_summary(item)}")
    return lines


def _risk_text(item: dict[str, Any]) -> str:
    risks = list(item.get("risk_flags") or [])
    if item.get("news_status") in {"NO_NEWS", "SKIPPED"} and not _signal_news_summary(item).startswith("系统信号摘要"):
        risks.append("资讯不足")
    try:
        if float(item.get("price_1y_pct") or 0) > 1:
            risks.append("一年涨幅过高，追高风险")
    except (TypeError, ValueError):
        pass
    return " | ".join(risks[:4]) or "需人工核对实时行情、公告、新闻和持仓冲突"


def _decision_text(item: dict[str, Any]) -> str:
    if item.get("status") == "research_candidate":
        return "可加入模拟观察，等待你确认。"
    return "高风险观察，不进入模拟候选。"


def _market_label(item: dict[str, Any]) -> str:
    labels = {"A": "A股", "HK": "港股", "US": "美股"}
    return labels.get(str(item.get("market")), str(item.get("market") or ""))


def _headline(item: dict[str, Any], index: int) -> str:
    return f"{index}. {_market_label(item)} {item.get('symbol')} · {_compact_name(item)}"


def _card_for_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    matches = " | ".join((item.get("strategy_matches") or [])[:4]) or "策略信号不足"
    content = "\n".join(
        [
            f"**{_headline(item, index)}**",
            f"结论：{_decision_text(item)}",
            f"公司：{_company_profile(item)}",
            f"行情：现价 {_fmt_price(item.get('price'))}｜当日 {_fmt_pct((item.get('daily_change_pct') or 0) / 100)}｜1年 {_fmt_pct(item.get('price_1y_pct'))}",
            f"位置：买点 {_fmt_price(item.get('buy_point'))}｜止损 {_fmt_price(item.get('stop_loss'))}｜趋势 {'向上' if item.get('trend_up') else '待确认'}",
            f"理由：{matches}",
            "资讯摘要：",
            *_news_lines(item),
            f"风险：{_risk_text(item)}",
            "",
            "仅模拟研究，不接券商、不下单。",
        ]
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue" if item.get("status") == "research_candidate" else "yellow",
            "title": {"tag": "plain_text", "content": f"Aegis 候选：{item.get('symbol')} {_compact_name(item)}"},
        },
        "elements": [
            {"tag": "div", "text": _md(content)},
            {
                "tag": "action",
                "actions": [
                    _button("加入模拟观察", "aegis_watch", item, "primary"),
                    _button("暂不关注", "aegis_ignore", item, "default"),
                    _button("要更多资讯", "aegis_more_news", item, "default"),
                    _button("我已外部手动处理", "aegis_manual_external", item, "danger"),
                ],
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "按钮只回传研究需求/反馈证据，不会触发真实交易。",
                    }
                ],
            },
        ],
    }


def _presentation_for_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    matches = " | ".join((item.get("strategy_matches") or [])[:4]) or "策略信号不足"
    body = "\n".join(
        [
            f"**{_headline(item, index)}**",
            f"结论：{_decision_text(item)}",
            f"公司：{_company_profile(item)}",
            f"行情：现价 `{_fmt_price(item.get('price'))}`｜当日 `{_fmt_pct((item.get('daily_change_pct') or 0) / 100)}`｜1年 `{_fmt_pct(item.get('price_1y_pct'))}`",
            f"位置：买点 `{_fmt_price(item.get('buy_point'))}`｜止损 `{_fmt_price(item.get('stop_loss'))}`｜趋势 `{'向上' if item.get('trend_up') else '待确认'}`",
            f"理由：{matches}",
            "资讯摘要：",
            *_news_lines(item),
            f"风险：{_risk_text(item)}",
        ]
    )
    command_prefix = f"Aegis反馈 {item.get('market')} {item.get('symbol')} {item.get('name')}"
    return {
        "title": f"Aegis 候选 {index}: {item.get('symbol')} {_compact_name(item)}",
        "tone": "success" if item.get("status") == "research_candidate" else "warning",
        "blocks": [
            {"type": "text", "text": body},
            {"type": "divider"},
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "加入模拟观察",
                        "style": "primary",
                        "action": {"type": "command", "command": f"{command_prefix} 加入模拟观察"},
                    },
                    {
                        "label": "暂不关注",
                        "style": "default",
                        "action": {"type": "command", "command": f"{command_prefix} 暂不关注"},
                    },
                    {
                        "label": "要更多资讯",
                        "style": "default",
                        "action": {"type": "command", "command": f"{command_prefix} 要更多资讯"},
                    },
                ],
            },
            {
                "type": "context",
                "text": "仅模拟研究。按钮只向股票助手回传你的研究反馈，不触发真实交易、券商 API、Webhook 或下单。",
            },
        ],
    }


def build_cards(limit: int = 6) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    workbench = json.loads(WORKBENCH.read_text(encoding="utf-8"))
    items = [
        item
        for item in workbench.get("candidates", [])
        if item.get("status") in {"research_candidate", "high_risk_watch"}
    ]
    items = sorted(
        items,
        key=lambda item: (
            item.get("news_status") == "PASS",
            item.get("status") == "research_candidate",
            item.get("score") or 0,
        ),
        reverse=True,
    )[:limit]
    cards = [_card_for_item(item, index) for index, item in enumerate(items, 1)]
    presentations = [_presentation_for_item(item, index) for index, item in enumerate(items, 1)]
    report = {
        "type": "aegis_stock_assistant_feishu_cards",
        "status": "PASS" if cards else "NO_CARDS",
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(),
        "card_count": len(cards),
        "presentation_count": len(presentations),
        "source_workbench_sha256": _sha256(WORKBENCH),
        "output": str(OUTPUT),
        "presentation_output": str(PRESENTATION_OUTPUT),
        "safety": {
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "feedback_evidence_only": True,
        },
    }
    report["_presentations"] = presentations
    return cards, report


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    cards, report = build_cards()
    presentations = report.pop("_presentations")
    OUTPUT.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    PRESENTATION_OUTPUT.write_text(json.dumps(presentations, ensure_ascii=False, indent=2), encoding="utf-8")
    report["output_sha256"] = _sha256(OUTPUT)
    report["presentation_output_sha256"] = _sha256(PRESENTATION_OUTPUT)
    OUTPUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cards={OUTPUT}")
    print(f"cards_sha256={report['output_sha256']}")
    print(f"presentations={PRESENTATION_OUTPUT}")
    print(f"presentations_sha256={report['presentation_output_sha256']}")
    print(f"report={OUTPUT_REPORT}")
    print(f"status={report['status']}")
    print(f"card_count={report['card_count']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

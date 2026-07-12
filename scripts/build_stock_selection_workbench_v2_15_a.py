#!/usr/bin/env python3
"""Build a Dashboard-readable stock selection workbench.

This script adapts the local OpenClaw stock-picker into Aegis as a read-only
candidate source. It never places orders, never writes production trades, and
never prints secrets.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "data" / "reports"
STOCK_PICKER_DIR = Path("/Users/weihongwang/shared-vault-workflow/stock-picker")
OUTPUT = REPORTS_DIR / "stock_selection_workbench_latest.json"
NEWS_DIGEST_OUTPUT = REPORTS_DIR / "stock_selection_news_digest_latest.md"
NEWS_ENRICH_LIMIT = 18
NEWS_ITEMS_PER_SYMBOL = 3


STRATEGY_BLUEPRINTS = [
    {
        "id": "qvm",
        "name": "质量 + 价值 + 动量",
        "use_for": "A/US/HK 通用主筛选",
        "signals": ["ROE/现金流质量", "估值不过热", "3-12个月动量", "风险过滤"],
        "source": "OpenClaw stock-picker + public factor research",
    },
    {
        "id": "low_vol_momentum",
        "name": "低波动 + 动量",
        "use_for": "避免只追涨，优先找趋势中但风险可承受的标的",
        "signals": ["近30日/中期动量", "20日波动率", "最大回撤", "止损距离"],
        "source": "Low-volatility / momentum factor literature",
    },
    {
        "id": "a_share_short_momentum",
        "name": "A股短周期动量 + 质量护栏",
        "use_for": "适应A股热点轮动快的市场结构",
        "signals": ["成交额", "短周期动量", "现金流质量", "过热降权"],
        "source": "OpenClaw stock-picker A股扫描 + A股因子动量研究",
    },
    {
        "id": "hk_smart_beta",
        "name": "港股 Smart Beta 六因子",
        "use_for": "港股候选池恢复后使用",
        "signals": ["价值", "低波动", "动量", "质量", "股息", "规模"],
        "source": "Hong Kong smart beta research",
    },
    {
        "id": "growth_breakout",
        "name": "成长突破 / CAN SLIM 候选",
        "use_for": "只作研究候选，不直接给交易动作",
        "signals": ["增长", "相对强度", "技术突破", "成交量确认"],
        "source": "CAN SLIM-style public screening literature",
    },
    {
        "id": "ai_photonics_supply_chain",
        "name": "AI 光子学供应链瓶颈",
        "use_for": "参考 Serenity/白毛股神式主题研究，只作线索，不直接推荐",
        "signals": ["光互连/光子学瓶颈", "上游稀缺环节", "收入放量验证", "估值过热否决"],
        "source": "User AI-news archive + public photonics supply-chain research",
    },
]


PUBLIC_RESEARCH_SOURCES = [
    {
        "name": "S&P DJI Hong Kong Smart Beta research",
        "url": "https://www.spglobal.com/spdji/en/documents/research/research-how-smart-beta-strategies-work-in-the-hong-kong-market.pdf",
        "takeaway": "港股可用 size/value/low volatility/momentum/quality/dividend 等因子，但需要分市场验证。",
    },
    {
        "name": "Tsinghua PBCSF A-share factor momentum paper",
        "url": "https://cfrc.pbcsf.tsinghua.edu.cn/__local/4/AE/67/89980D797AD790C70C6AD15BEAB_F3C5BFB8_73992.pdf",
        "takeaway": "A股因子动量有实证价值，但应加风险和情绪状态过滤。",
    },
    {
        "name": "Alpha Architect low-volatility momentum note",
        "url": "https://alphaarchitect.com/low-volatility-momentum-factor-investing-portfolios/",
        "takeaway": "动量与低波动组合可降低只追高带来的心理和回撤压力。",
    },
    {
        "name": "QVM public screener description",
        "url": "https://www.quant-investing.com/blog/quality-value-momentum-the-best-strategy-you-have-never-heard-of",
        "takeaway": "质量、估值和价格动量可组合成可解释的多因子筛选。",
    },
]


HK_EODHD_UNIVERSE = [
    ("0700.HK", "00700", "腾讯控股"),
    ("9988.HK", "09988", "阿里巴巴-W"),
    ("3690.HK", "03690", "美团-W"),
    ("9618.HK", "09618", "京东集团-SW"),
    ("1810.HK", "01810", "小米集团-W"),
    ("0005.HK", "00005", "汇丰控股"),
    ("1299.HK", "01299", "友邦保险"),
    ("2318.HK", "02318", "中国平安"),
    ("0941.HK", "00941", "中国移动"),
    ("0883.HK", "00883", "中国海洋石油"),
    ("0388.HK", "00388", "香港交易所"),
    ("1211.HK", "01211", "比亚迪股份"),
    ("2333.HK", "02333", "长城汽车"),
    ("1398.HK", "01398", "工商银行"),
    ("3988.HK", "03988", "中国银行"),
]

US_EODHD_UNIVERSE = [
    ("VRTX.US", "VRTX", "Vertex Pharmaceuticals"),
    ("AMAT.US", "AMAT", "Applied Materials"),
    ("HOOD.US", "HOOD", "Robinhood Markets"),
    ("PANW.US", "PANW", "Palo Alto Networks"),
    ("KLAC.US", "KLAC", "KLA Corporation"),
    ("RBLX.US", "RBLX", "Roblox"),
    ("BAC.US", "BAC", "Bank of America"),
    ("NET.US", "NET", "Cloudflare"),
    ("OKTA.US", "OKTA", "Okta"),
    ("MRNA.US", "MRNA", "Moderna"),
    ("NVDA.US", "NVDA", "NVIDIA"),
    ("MSFT.US", "MSFT", "Microsoft"),
    ("GOOGL.US", "GOOGL", "Alphabet"),
    ("TSLA.US", "TSLA", "Tesla"),
]

NEWS_ALIASES = {
    "00005": ["HSBC"],
    "00700": ["Tencent"],
    "09988": ["Alibaba"],
    "03690": ["Meituan"],
    "09618": ["JD.com", "JD"],
    "01810": ["Xiaomi"],
    "01299": ["AIA"],
    "02318": ["Ping An"],
    "00941": ["China Mobile"],
    "00883": ["CNOOC"],
    "00388": ["Hong Kong Exchanges", "HKEX"],
    "01211": ["BYD"],
    "02333": ["Great Wall Motor"],
    "01398": ["ICBC"],
    "03988": ["Bank of China"],
}

NEWS_TRANSLATIONS = [
    (
        "Vertex (VRTX) Wins FDA Expansion For CASGEVY And Advances ALYFTREK In Canada",
        "Vertex：CASGEVY 获 FDA 扩大适应症批准，ALYFTREK 在加拿大推进。",
    ),
    (
        "Vertex Pharmaceuticals Bets $10 Billion on Crinetics to Build Endocrinology Powerhouse",
        "Vertex 拟以约 100 亿美元押注 Crinetics，扩展内分泌业务。",
    ),
    (
        "Goldman Sachs doubles down on Applied Materials stock target",
        "Goldman Sachs 重申看好 Applied Materials 目标价，需继续核对估值与周期位置。",
    ),
    (
        "Amazon, Microsoft and Meta Among HSBC Earnings Picks",
        "HSBC 财报季关注名单提到 Amazon、Microsoft、Meta，说明大型科技仍是机构重点线索。",
    ),
    (
        "HSBC Tightens Private Credit Strategy Amid Rising Sector Concerns",
        "HSBC 在行业担忧升温下收紧私募信贷策略，偏风险控制信号。",
    ),
    (
        "Stock Market Today: Dow Ends Higher; SK Hynix Jumps In U.S. Trading Debut; Moderna Tumbles",
        "美股日报：道指收高，SK Hynix 美股首秀上涨，Moderna 下跌。",
    ),
    (
        "Cathie Wood buys $22.8 million of surging tech stock",
        "Cathie Wood 买入约 2280 万美元热门科技股，HOOD 仍需警惕情绪拥挤。",
    ),
    (
        "5 Top AI Stocks Investors Own on Robinhood",
        "Robinhood 投资者持有的热门 AI 股票名单，可作为散户偏好温度计。",
    ),
    (
        "Insider trades: Palo Alto Networks, Taiwan Semiconductor, and Sony among major names",
        "内部人交易追踪提到 Palo Alto Networks、TSMC、Sony 等重点公司。",
    ),
    (
        "RBLX SHAREHOLDER NOTICE: Faruqi & Faruqi, LLP Notifies Roblox (RBLX) Investors of Securities Class Action Lawsuit Deadline on August 7, 2026",
        "Roblox：律所提醒证券集体诉讼截止日期，属于法律/声誉风险线索。",
    ),
]

NEWS_TERM_TRANSLATIONS = {
    "SHAREHOLDER NOTICE": "股东提醒",
    "Securities Class Action Lawsuit": "证券集体诉讼",
    "Investors": "投资者",
    "Deadline": "截止日期",
    "among major names": "等重点公司",
    "Tumbles": "下跌",
    "Jumps": "上涨",
    "Ends Higher": "收高",
    "Earnings Picks": "财报季关注名单",
    "Private Credit Strategy": "私募信贷策略",
    "Rising Sector Concerns": "行业担忧升温",
    "stock target": "目标价",
    "doubles down on": "重申看好",
    "Bets": "押注",
    "Powerhouse": "业务平台",
}


def _display_news_text(title: str, summary: str = "") -> str:
    """Return a short Chinese-first display summary for Dashboard/Feishu."""
    source = (summary or title or "").strip()
    if not source:
        return "暂无可靠资讯摘要。"
    for needle, translated in NEWS_TRANSLATIONS:
        if needle in title or needle in source:
            return translated
    text = source
    for old, new in NEWS_TERM_TRANSLATIONS.items():
        text = text.replace(old, new)
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return text[:160]
    return f"英文资讯摘要：{text[:150]}"


def _load_stock_picker_env() -> None:
    env_path = STOCK_PICKER_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ[key] = val


def _run_screen(label: str, fn) -> dict[str, Any]:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            text, results, scanned = fn()
        return {
            "market": label,
            "status": "PASS" if results else "NO_CANDIDATES",
            "scanned_count": scanned,
            "raw_count": len(results),
            "raw_text_excerpt": str(text)[:700],
            "logs_excerpt": buffer.getvalue()[-1200:],
            "results": results,
        }
    except Exception as exc:  # pragma: no cover - defensive report boundary
        return {
            "market": label,
            "status": "FAIL",
            "scanned_count": 0,
            "raw_count": 0,
            "error": f"{type(exc).__name__}: {exc}",
            "logs_excerpt": buffer.getvalue()[-1200:],
            "results": [],
        }


def _fetch_eodhd_daily(symbol: str, token: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "api_token": token,
            "fmt": "json",
            "period": "d",
            "from": "2026-01-01",
            "to": dt.date.today().isoformat(),
        }
    )
    url = f"https://eodhd.com/api/eod/{urllib.parse.quote(symbol)}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "ProjectAegis/0.1 hk-selection"})
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.loads(response.read(500000).decode("utf-8"))
    return payload if isinstance(payload, list) else []


def _build_hk_candidate(provider_symbol: str, code: str, name: str, token: str) -> dict[str, Any] | None:
    rows = _fetch_eodhd_daily(provider_symbol, token)
    closes = [float(row.get("adjusted_close") or row.get("close") or 0) for row in rows]
    closes = [x for x in closes if x > 0]
    if len(closes) < 20:
        return None
    current = closes[-1]
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
    support = min(closes[-60:]) if len(closes) >= 60 else min(closes[-20:])
    buy_point = round(ma20 * 0.98, 3)
    stop_loss = round(buy_point * 0.85, 3)
    trend_up = current >= ma20 and ma20 >= ma60
    momentum_20 = (current - closes[-20]) / closes[-20] if closes[-20] else 0
    price_1y_pct = (current - closes[0]) / closes[0] if closes[0] else None
    score = 0
    hits: list[str] = []
    if trend_up:
        score += 10
        hits.append("↑趋势")
    else:
        score -= 3
        hits.append("趋势未确认")
    if abs(current - buy_point) / buy_point <= 0.04:
        score += 10
        hits.append("📍近买点")
    if momentum_20 > 0.05:
        score += 5
        hits.append("20日动量强")
    if price_1y_pct is not None and price_1y_pct > 0.25:
        score += 3
        hits.append("年内正动量")
    return {
        "code": code,
        "name": name,
        "price": current,
        "pct": momentum_20 * 100,
        "pe": None,
        "score": score,
        "hits": hits,
        "basic_pass": True,
        "basic_reasons": [],
        "skipped": ["财报(HK EODHD轻量)", "估值"],
        "buy": {
            "current": round(current, 3),
            "ma20": round(ma20, 3),
            "support": round(support, 3),
            "buy_point": buy_point,
            "stop_loss": stop_loss,
            "target_price": None,
            "risk_reward": None,
            "trend_up": trend_up,
        },
        "price_1y_pct": price_1y_pct,
        "description": "EODHD 港股日线轻量候选",
    }


def _screen_eodhd_universe(
    market: str,
    universe: list[tuple[str, str, str]],
    top_n: int = 10,
) -> tuple[str, list[dict[str, Any]], int]:
    token = os.environ.get("AEGIS_EODHD_API_TOKEN", "").strip()
    if not token:
        return f"⚠️ {market} 选股需要 AEGIS_EODHD_API_TOKEN", [], 0
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    executor = ThreadPoolExecutor(max_workers=6)
    try:
        future_map = {
            executor.submit(_build_hk_candidate, provider_symbol, code, name, token): provider_symbol
            for provider_symbol, code, name in universe
        }
        try:
            for future in as_completed(future_map, timeout=18):
                provider_symbol = future_map[future]
                try:
                    item = future.result(timeout=1)
                    if item:
                        if market == "US":
                            item["description"] = "EODHD 美股日线轻量候选"
                        results.append(item)
                except Exception as exc:
                    errors.append(f"{provider_symbol}:{type(exc).__name__}")
        except FuturesTimeoutError:
            errors.append(f"{market.lower()}_eodhd_global_timeout")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    ranked = sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]
    for index, item in enumerate(ranked, 1):
        item["rank"] = index
    today = dt.date.today()
    text = f"{market} 选股 {today} EODHD扫描 {len(universe)} 只 → 候选 {len(ranked)} 只"
    if errors:
        text += f"；部分失败 {', '.join(errors[:5])}"
    return text, ranked, len(universe)


def _screen_hk_eodhd(top_n: int = 10) -> tuple[str, list[dict[str, Any]], int]:
    return _screen_eodhd_universe("HK", HK_EODHD_UNIVERSE, top_n=top_n)


def _screen_us_eodhd(top_n: int = 10) -> tuple[str, list[dict[str, Any]], int]:
    return _screen_eodhd_universe("US", US_EODHD_UNIVERSE, top_n=top_n)



def _risk_flags(item: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if not item.get("basic_pass", False):
        flags.extend(item.get("basic_reasons") or ["未通过基础筛选"])
    if (item.get("price_1y_pct") or 0) > 3.0:
        flags.append("一年涨幅超过300%，过热降权")
    if (item.get("pct") or 0) < -6:
        flags.append("当日跌幅较大，需要等企稳")
    buy = item.get("buy") or {}
    if buy.get("trend_up") is False:
        flags.append("趋势向下，暂不追")
    if buy.get("stop_loss") and item.get("price") and item["price"] <= buy["stop_loss"]:
        flags.append("价格触及或跌破止损线")
    if buy.get("risk_reward") is not None and buy["risk_reward"] <= 0:
        flags.append("买点赔率为负或目标价异常")
    if any("现金流差" in str(hit) or "现金流质量极差" in str(hit) for hit in item.get("hits", [])):
        flags.append("现金流质量风险")
    return flags


def _decision_status(item: dict[str, Any], market: str) -> str:
    flags = _risk_flags(item)
    score = item.get("score") or 0
    if not item.get("basic_pass", False):
        return "blocked"
    if any("趋势向下" in x for x in flags):
        return "high_risk_watch"
    if any("超过300%" in x or "赔率为负" in x for x in flags):
        return "high_risk_watch"
    if score >= 10:
        return "research_candidate"
    return "watch"


def _normalize(item: dict[str, Any], market: str) -> dict[str, Any]:
    flags = _risk_flags(item)
    status = _decision_status(item, market)
    buy = item.get("buy") or {}
    return {
        "symbol": item.get("code"),
        "name": item.get("name") or item.get("code"),
        "market": market,
        "rank": item.get("rank"),
        "price": item.get("price"),
        "daily_change_pct": item.get("pct"),
        "score": item.get("score"),
        "status": status,
        "status_label": {
            "research_candidate": "可研究",
            "high_risk_watch": "高风险观察",
            "watch": "观察",
            "blocked": "暂不碰",
        }.get(status, "观察"),
        "strategy_matches": item.get("hits", []),
        "risk_flags": flags,
        "basic_pass": item.get("basic_pass", False),
        "skipped": item.get("skipped", []),
        "industry_or_description": item.get("description", ""),
        "buy_point": buy.get("buy_point"),
        "stop_loss": buy.get("stop_loss"),
        "trend_up": buy.get("trend_up"),
        "price_1y_pct": item.get("price_1y_pct"),
        "user_action": _user_action(status),
        "real_trade_allowed": False,
    }


def _user_action(status: str) -> str:
    if status == "research_candidate":
        return "加入模拟研究候选；人工核对实时行情、公告、新闻和持仓冲突后，才允许记录纸面模拟。"
    if status == "high_risk_watch":
        return "只观察，不模拟开仓；等过热、止损距离或赔率问题改善。"
    if status == "blocked":
        return "暂不碰；除非基础筛选或风险条件变化。"
    return "继续观察，等待更强证据。"


def _news_market(market: str) -> str:
    if market in {"A", "HK"}:
        return market
    return "US"


def _eodhd_news_symbol(item: dict[str, Any]) -> str | None:
    market = str(item.get("market") or "")
    symbol = str(item.get("symbol") or "")
    if market == "US":
        return f"{symbol}.US" if "." not in symbol else symbol
    if market == "HK":
        code = symbol.split(".")[0].lstrip("0") or "0"
        return f"{code.zfill(4)}.HK"
    if market == "A":
        code = symbol.split(".")[0]
        if len(code) == 6:
            return f"{code}.SHG" if code.startswith("6") else f"{code}.SHE"
    return None


def _clean_news_item(item: dict[str, Any]) -> dict[str, str]:
    title = str(item.get("title") or "").strip()
    summary = str(item.get("body") or item.get("snippet") or "").strip()[:260]
    return {
        "title": title,
        "source": str(item.get("source") or "").strip(),
        "url": str(item.get("url") or item.get("link") or "").strip(),
        "date": str(item.get("date") or item.get("published") or "").strip()[:19],
        "summary": summary,
        "display_summary": _display_news_text(title, summary),
    }


def _news_relevance_tokens(item: dict[str, Any]) -> list[str]:
    symbol = str(item.get("symbol") or "").split(".")[0]
    name = str(item.get("name") or "")
    tokens = [symbol]
    tokens.extend(NEWS_ALIASES.get(symbol, []))
    for raw in name.replace(",", " ").replace(".", " ").replace("-", " ").split():
        token = raw.strip()
        if len(token) >= 4 and token.lower() not in {"incorporated", "corporation", "limited"}:
            tokens.append(token)
    if name and any("\u4e00" <= ch <= "\u9fff" for ch in name):
        tokens.append(name)
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        key = token.lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(token)
    return unique


def _is_relevant_news(item: dict[str, Any], news: dict[str, str]) -> bool:
    text = " ".join([news.get("title", ""), news.get("summary", ""), news.get("url", "")]).lower()
    return any(token.lower() in text for token in _news_relevance_tokens(item))


def _search_eodhd_news(item: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    token = os.environ.get("AEGIS_EODHD_API_TOKEN", "").strip()
    provider_symbol = _eodhd_news_symbol(item)
    if not token or not provider_symbol:
        return [], "missing_eodhd_token_or_symbol"
    params = urllib.parse.urlencode(
        {
            "s": provider_symbol,
            "api_token": token,
            "fmt": "json",
            "limit": NEWS_ITEMS_PER_SYMBOL,
        }
    )
    url = f"https://eodhd.com/api/news?{params}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ProjectAegis/0.1 news"})
        with urllib.request.urlopen(request, timeout=7) as response:
            payload = json.loads(response.read(300000).decode("utf-8"))
    except Exception as exc:
        return [], f"eodhd_news_{type(exc).__name__}"
    if not isinstance(payload, list):
        return [], "eodhd_news_unexpected_payload"
    news_items = [
        clean
        for clean in (_clean_news_item(raw) for raw in payload if isinstance(raw, dict))
        if (clean["title"] or clean["url"]) and _is_relevant_news(item, clean)
    ][:NEWS_ITEMS_PER_SYMBOL]
    return news_items, "eodhd_news"


def _search_company_news_subprocess(item: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    code = str(item.get("symbol") or "")
    name = str(item.get("name") or "")
    market = _news_market(str(item.get("market") or ""))
    snippet = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(STOCK_PICKER_DIR)!r})\n"
        "from news_search import search_company_news\n"
        f"items = search_company_news({name!r}, {code!r}, {market!r}, max_results={NEWS_ITEMS_PER_SYMBOL})\n"
        "print(json.dumps(items, ensure_ascii=False))\n"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", snippet],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [], "timeout"
    if completed.returncode != 0:
        return [], (completed.stderr or completed.stdout)[-500:]
    try:
        payload = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return [], completed.stdout[-500:]
    news_items = [
        clean
        for clean in (_clean_news_item(raw) for raw in payload if isinstance(raw, dict))
        if clean["title"] or clean["url"]
    ][:NEWS_ITEMS_PER_SYMBOL]
    return news_items, (completed.stderr or "")[-500:]


def _enrich_news(candidates: list[dict[str, Any]]) -> None:
    """Attach read-only company news to top candidates without changing scores."""
    targets = [
        item
        for item in candidates
        if item.get("status") in {"research_candidate", "high_risk_watch"}
    ][:NEWS_ENRICH_LIMIT]
    target_ids = {id(item) for item in targets}

    for item in candidates:
        if id(item) not in target_ids:
            item["news_status"] = "SKIPPED"
            item["news_items"] = []
            item["news_summary"] = "未进入本轮资讯抓取上限。"

    for item in targets:
        try:
            news_items, logs = _search_eodhd_news(item)
            if not news_items and os.environ.get("AEGIS_LIVE_DDG_NEWS") == "1":
                news_items, logs = _search_company_news_subprocess(item)
            item["news_status"] = "PASS" if news_items else "NO_NEWS"
            item["news_items"] = news_items
            item["news_summary"] = " | ".join(x.get("display_summary") or x["title"] for x in news_items[:2]) or "未找到近期公司动态。"
            item["news_logs_excerpt"] = logs[-500:]
        except Exception as exc:  # pragma: no cover - external network boundary
            item["news_status"] = "ERROR"
            item["news_items"] = []
            item["news_summary"] = f"新闻搜索失败：{type(exc).__name__}"
            item["news_logs_excerpt"] = ""


def _news_cache_from_candidates(candidates: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    cache: dict[tuple[str, str], dict[str, Any]] = {}
    for item in candidates:
        key = (str(item.get("market") or ""), str(item.get("symbol") or ""))
        if not key[0] or not key[1]:
            continue
        news_items = item.get("news_items") or []
        news_summary = item.get("news_summary") or ""
        if item.get("news_status") in {"PASS", "CACHED"} and (news_items or news_summary):
            cache[key] = {
                "news_items": news_items,
                "news_summary": news_summary,
                "news_logs_excerpt": item.get("news_logs_excerpt", ""),
            }
    return cache


def _apply_cached_news(candidates: list[dict[str, Any]], cache: dict[tuple[str, str], dict[str, Any]]) -> None:
    for item in candidates:
        if item.get("news_status") == "PASS":
            continue
        key = (str(item.get("market") or ""), str(item.get("symbol") or ""))
        cached = cache.get(key)
        if not cached:
            continue
        item["news_status"] = "CACHED"
        item["news_items"] = cached.get("news_items") or []
        item["news_summary"] = cached.get("news_summary") or "使用最近一次已验证资讯摘要。"
        item["news_logs_excerpt"] = "fallback_cached_previous_workbench"


def _news_enriched_count(candidates: list[dict[str, Any]]) -> int:
    return sum(1 for x in candidates if x.get("news_status") in {"PASS", "CACHED"})


def _mark_news_deferred(candidates: list[dict[str, Any]], reason: str) -> None:
    for item in candidates:
        item.setdefault("news_status", "DEFERRED")
        item.setdefault("news_items", [])
        item.setdefault("news_summary", reason)


def _render_news_digest(report: dict[str, Any]) -> str:
    generated = report.get("generated_at", "")
    lines = [
        "# Project Aegis 选股 + 资讯简报",
        "",
        f"- Generated At: {generated}",
        f"- Overall Status: {report.get('overall_status')}",
        f"- Markets: {', '.join(report.get('summary', {}).get('markets_passed', []))}",
        f"- Research Candidates: {report.get('summary', {}).get('research_candidate_count')}",
        "- Boundary: 仅供模拟研究；不下单、不接券商、不生成真实交易指令。",
        "",
    ]
    for item in report.get("candidates", [])[:NEWS_ENRICH_LIMIT]:
        currency = "US$" if item.get("market") == "US" else "HK$" if item.get("market") == "HK" else "CNY"
        lines.extend(
            [
                f"## {item.get('market')} {item.get('symbol')} {item.get('name')}",
                "",
                f"- Status: {item.get('status_label')} / Score: {item.get('score')}",
                f"- Price: {currency} {item.get('price')} / Change: {item.get('daily_change_pct')}",
                f"- Why: {' | '.join((item.get('strategy_matches') or [])[:4]) or '策略信号不足'}",
                f"- Risk: {' | '.join((item.get('risk_flags') or [])[:3]) or '需人工核对实时行情、公告、新闻'}",
                f"- Use: {item.get('user_action')}",
                "",
                "### 公司动态",
            ]
        )
        news_items = item.get("news_items") or []
        if not news_items:
            lines.append(f"- {item.get('news_summary') or '未找到近期公司动态。'}")
        else:
            for news in news_items:
                meta = " · ".join(x for x in [news.get("date"), news.get("source")] if x)
                suffix = f" ({meta})" if meta else ""
                url = news.get("url")
                if url:
                    lines.append(f"- [{news.get('title')}]({url}){suffix}")
                else:
                    lines.append(f"- {news.get('title')}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_report() -> dict[str, Any]:
    _load_stock_picker_env()
    sys.path.insert(0, str(STOCK_PICKER_DIR))
    previous_news_cache: dict[tuple[str, str], dict[str, Any]] = {}
    if OUTPUT.exists():
        previous_payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
        previous_news_cache = _news_cache_from_candidates(previous_payload.get("candidates", []))
    if os.environ.get("AEGIS_LIVE_DEEP_SCAN") != "1" and OUTPUT.exists():
        cached = previous_payload
        cached["generated_at"] = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
        cached["refresh_mode"] = "cached_fast_default"
        cached["source"] = "Cached Aegis stock selection workbench; set AEGIS_LIVE_DEEP_SCAN=1 for full live refresh"
        cached["strategy_blueprints"] = STRATEGY_BLUEPRINTS
        cached["public_research_sources"] = PUBLIC_RESEARCH_SOURCES
        _enrich_news(cached.get("candidates", []))
        _apply_cached_news(cached.get("candidates", []), previous_news_cache)
        cached.setdefault("summary", {})["news_enriched_count"] = _news_enriched_count(cached.get("candidates", []))
        cached.setdefault("summary", {})["news_cached_fallback_count"] = sum(
            1 for x in cached.get("candidates", []) if x.get("news_status") == "CACHED"
        )
        return cached

    from market_screener import screen_a

    runs = [
        _run_screen("A", lambda: screen_a(top_n=10, deep_n=40)),
        _run_screen("HK", lambda: _screen_hk_eodhd(top_n=10)),
        _run_screen("US", lambda: _screen_us_eodhd(top_n=10)),
    ]
    candidates = []
    for run in runs:
        candidates.extend(_normalize(item, run["market"]) for item in run["results"])

    ranked = sorted(
        candidates,
        key=lambda x: (
            {"research_candidate": 3, "high_risk_watch": 2, "watch": 1, "blocked": 0}.get(x["status"], 0),
            x.get("score") or 0,
        ),
        reverse=True,
    )
    _enrich_news(ranked)
    _apply_cached_news(ranked, previous_news_cache)
    summary = {
        "total_candidates": len(ranked),
        "research_candidate_count": sum(1 for x in ranked if x["status"] == "research_candidate"),
        "high_risk_watch_count": sum(1 for x in ranked if x["status"] == "high_risk_watch"),
        "blocked_count": sum(1 for x in ranked if x["status"] == "blocked"),
        "news_enriched_count": _news_enriched_count(ranked),
        "news_cached_fallback_count": sum(1 for x in ranked if x.get("news_status") == "CACHED"),
        "markets_passed": [r["market"] for r in runs if r["status"] == "PASS"],
        "markets_failed_or_empty": [r["market"] for r in runs if r["status"] != "PASS"],
        "real_trade_allowed": False,
    }
    return {
        "stage": "V2.15-A Stock Selection Workbench",
        "overall_status": "PASS" if ranked else "NO_CANDIDATES",
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(),
        "source": "Aegis adapter over local OpenClaw stock-picker + company news search",
        "summary": summary,
        "safety": {
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_webhook": True,
            "no_position_size": True,
        },
        "strategy_blueprints": STRATEGY_BLUEPRINTS,
        "public_research_sources": PUBLIC_RESEARCH_SOURCES,
        "market_runs": [
            {k: v for k, v in run.items() if k != "results"}
            for run in runs
        ],
        "candidates": ranked,
    }


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    NEWS_DIGEST_OUTPUT.write_text(_render_news_digest(report), encoding="utf-8")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    news_digest = hashlib.sha256(NEWS_DIGEST_OUTPUT.read_bytes()).hexdigest()
    print(f"output={OUTPUT}")
    print(f"sha256={digest}")
    print(f"news_digest={NEWS_DIGEST_OUTPUT}")
    print(f"news_digest_sha256={news_digest}")
    print(f"overall_status={report['overall_status']}")
    print(f"research_candidate_count={report['summary']['research_candidate_count']}")
    print(f"news_enriched_count={report['summary']['news_enriched_count']}")
    print(f"markets_passed={','.join(report['summary']['markets_passed'])}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

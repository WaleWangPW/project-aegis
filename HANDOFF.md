# Project Aegis HANDOFF

## 2026-07-12 Update: Strategy-Specific Historical Cases V1

- GitHub connectivity checked with `gh`: connected account is `WaleWangPW`.
- Active GitHub auth source is `GITHUB_TOKEN` with `public_repo` only; keyring also has a non-active `WaleWangPW` token with broader `repo/read:org/workflow` scopes. No token value was printed.
- Public GitHub repository created and pushed: `https://github.com/WaleWangPW/project-aegis`.
- Current remote: `origin https://github.com/WaleWangPW/project-aegis.git`; default branch `main`; current public snapshot commit `eaacc8b Initial Project Aegis public snapshot`.
- Public snapshot was pushed after secret/path checks: `.env`, `data/cache/`, `.venv/`, `.playwright-cli/`, and known API-token strings were not tracked.
- Added `scripts/build_aegis_strategy_specific_historical_cases.py`.
- New report generated: `data/reports/aegis_strategy_specific_historical_cases_latest.json`, status `PASS`.
- Current strategy-specific historical cases: 13 research candidates, 11 candidates with cases, 44 historical cases total, 2 data gaps.
- A-share cases assembled from existing point-in-time Tushare daily cache:
  - `603893 / 瑞芯微`: 4 cases, win rate `25%`, average return about `-3.99%`.
  - `300059 / 东方财富`: 4 cases, win rate `25%`, average return about `-3.89%`.
- EODHD/Twelve daily-bar refresh now covers 9 of 11 H/US candidates; remaining gaps are 00005.HK and PANW.
- Dashboard assets bumped through `v2.css?v=20260712g` and `v2.js?v=20260712g`.
- Dashboard `历史回测` drawer now displays `策略族代理`, `逐标的 case`, and `数据缺口`.
- Validation run:
  - `python3 -m py_compile scripts/build_aegis_strategy_specific_historical_cases.py` exit code `0`.
  - `node --check dashboard/v2.js` exit code `0`.
  - `python3 scripts/build_aegis_strategy_specific_historical_cases.py` exit code `0`.
  - Browser QA for `http://localhost:8080/dashboard/index.html?v=20260712g`: no console error/warn; strategy-specific case panel visible; 390px mobile width has no horizontal overflow.
- Safety boundary unchanged: case assembly only; no user-facing suggestion, no broker API, no webhook, no real order placement, no position sizing, no live order signal.
- Next stage: fix remaining 00005.HK and PANW daily-bar gaps, then evaluate assembled candidate cases before any simulation suggestion upgrade.

## 2026-07-12 Update: Strategy Sandbox Coverage Connected To Dashboard

- Current usable web entry remains `http://localhost:8080/dashboard/index.html`; HTTP check returned `200 OK`.
- Dashboard assets bumped through `v2.css?v=20260712f` and `v2.js?v=20260712f`.
- Added `scripts/build_aegis_strategy_sandbox_validation.py`.
- New report generated: `data/reports/aegis_strategy_sandbox_validation_latest.json`, status `PASS`.
- Strategy sandbox coverage summary: 13 current research candidates, 2 A-share candidates have point-in-time strategy-family proxy coverage, 11 candidates still require strategy-specific historical case assembly, direct candidate backtest count remains `0`.
- Dashboard now reads `aegis_strategy_sandbox_validation_latest.json` and shows a compact `策略沙盘验证` panel inside the `历史回测` drawer.
- Evidence details now link both `aegis_strategy_validation_input_latest.json` and `aegis_strategy_sandbox_validation_latest.json`.
- Validation run:
  - `python3 -m py_compile scripts/build_aegis_strategy_sandbox_validation.py` exit code `0`.
  - `node --check dashboard/v2.js` exit code `0`.
  - `python3 scripts/build_aegis_strategy_sandbox_validation.py` exit code `0`.
  - Browser QA for `http://localhost:8080/dashboard/index.html?v=20260712f`: no console error/warn; strategy sandbox panel visible after opening `历史回测`; 390px mobile width has no horizontal overflow.
- Git upload note: current `repo` path and nearby parents do not contain `.git`; no remote exists here, so no push was performed. Do not initialize or upload until the intended remote is provided or confirmed.
- Safety boundary unchanged: simulation/research only; no broker API, no webhook, no real order placement, no position sizing, no live order signal.
- Next stage: build true strategy-specific historical cases for the 11 pending candidates, especially US/HK and AI photonics/theme cases; do not treat proxy coverage as a buy signal.

## 2026-07-12 Update: Dashboard Low-Density Reading Mode

- User feedback: Dashboard text was still too dense. Canva can be used later for presentation/prototype work, but the live usable Dashboard should be optimized directly in HTML/CSS/JS first.
- Dashboard assets bumped through `v2.css?v=20260712e` and `v2.js?v=20260712e` to avoid browser/mobile cache.
- `selectionWorkbenchPanel` now shows only Top 3 priority research candidates by default; additional research candidates and high-risk watch items are collapsed behind details toggles.
- Strategy radar now shows 3 core strategies by default, with a `查看全部 6 个策略` details toggle.
- Stock cards now use low-density rows: company, reason, news, risk, levels, plus `展开详情` for full reasoning/risk/action text.
- Secondary information now uses drawer sections: risk blockers, holdings, watchlist, market status, and next check are collapsed by default with one-line summaries.
- Old simulation brief is collapsed by default as `旧建议简报：00700.HK`.
- Browser QA passed for `http://localhost:8080/dashboard/index.html?v=20260712e`: no console error/warn, Top 3 copy visible, additional candidate toggle visible, strategy toggle visible, 5 drawer sections present and closed by default.
- Mobile 390px QA passed: no horizontal overflow, Top 3 copy visible, more-candidate and more-strategy toggles visible.
- Safety boundary unchanged: simulation/research only; no broker API, no webhook, no real order placement.

## 2026-07-12 Update: Dashboard Visual Upgrade + Strategy Validation Entry

- Today's usable web entry remains `http://localhost:8080/dashboard/index.html`; local HTTP check returned `200 OK`.
- Dashboard cache busting is active through `v2.css?v=20260712b` and `v2.js?v=20260712b`, so desktop/mobile should not keep stale UI assets.
- Dashboard visual structure is now decision-first: status bar -> today's conclusion -> today's stock selection workbench -> risk/holdings/watchlist/details.
- Stock selection workbench currently shows: 30 total candidates, 13 research candidates, 9 news-enriched candidates, markets `A/HK/US` all passed, real trading disabled.
- US English news is now rendered Chinese-first through `display_summary`; examples verified on Dashboard include Vertex, Applied Materials, HSBC, Moderna, and Robinhood news summaries.
- Feishu card feedback backend self-test recorded `HOOD / aegis_more_news` in `data/records/aegis_stock_feedback_events.jsonl` and `data/reports/aegis_stock_feedback_latest.json`; safety effects remain all false.
- Dashboard now surfaces the latest feedback record and links `aegis_stock_feedback_latest.json` from system/evidence details.
- Strategy radar now includes 6 strategy families: QVM, low-vol momentum, A-share short momentum, HK smart beta, CAN SLIM-style growth breakout, and `AI 光子学供应链瓶颈` based on the Serenity/白毛股神 theme.
- `docs/STRATEGY_RESEARCH.md` records the strategy slate and historical validation plan.
- `data/reports/aegis_strategy_validation_input_latest.json` is `READY`, maps 13 research candidates to strategy IDs, and marks all as `pending_point_in_time_history_test`.
- Latest stock-assistant send result remains `SENT`, `sent_count=6`, `failed_count=0`, `transport=feishu_official_api_stock_app`, `account=stock`.
- Browser QA passed: page title correct, no console error/warn, 9 visible selection cards, 6 strategy cards, Chinese news visible, latest feedback visible; mobile 390px check had no horizontal overflow.
- Safety boundary unchanged: simulation/research only; no broker API, no webhook, no real order placement, no position sizing.

## 2026-07-12 Update: Usable Dashboard + News Summary Cards

- Today's usable web entry is live at `http://localhost:8080/dashboard/index.html`; local HTTP check returned `200 OK`.
- `stock_selection_workbench_latest.json` is `PASS`: 30 total candidates, 13 research candidates, 11 news-enriched candidates, markets `A/HK/US` all passed, real trading disabled.
- Dashboard `v2.js` now renders company news as short summaries in the selection cards instead of link-heavy article lists.
- Feishu stock-assistant cards were rebuilt to prioritize candidates with news coverage. Current 6 cards: `603893`, `VRTX`, `AMAT`, `00005`, `MRNA`, `HOOD`; all have news summaries.
- Latest stock-assistant send result: `SENT`, `sent_count=6`, `failed_count=0`, `transport=feishu_official_api_stock_app`, `account=stock`.
- Safety boundary unchanged: simulation/research only; no broker API, no webhook, no real order placement.

## 2026-07-12 Update: Stock Assistant Feishu Delivery Fixed

- User-facing Feishu push must use the `stock` OpenClaw/Feishu account (`股票助手`), not the AI-news app (`AI资讯助手`).
- Root cause found: `stock-picker/.env` points at the AI-news app target, and OpenClaw `message send --account stock` currently fails in its Feishu plugin token path with `ERR_FR_TOO_MANY_REDIRECTS`; the stock Feishu app itself is valid.
- Fix landed in `scripts/send_aegis_stock_feishu_cards_via_stock_assistant.py`: it still attempts `openclaw message send --account stock` first, then falls back to Feishu official API using the stock app token and `feishu-stock-allowFrom.json`. It does not print or record secrets.
- Latest send result: `data/reports/aegis_stock_assistant_feishu_send_latest.json`, `send_status=SENT`, `sent_count=6`, `failed_count=0`, `transport=feishu_official_api_stock_app`, `account=stock`.
- Current card content now includes company situation, latest news when available, 1Y performance, price/day move, buy point, stop loss, reason, risk, and simulation-only feedback buttons.
- Safety boundary remains unchanged: simulation/research only; no broker API, no webhook, no real order placement.

> Current canonical entry has moved to `docs/ROADMAP.md`,
> `docs/HANDOFF.md`, and `docs/OPENCLAW_RUNBOOK.md`.
> This root handoff is a historical P22-era note and must not be used as the
> current project state. Current product version:
> `V2.12-J H-US Virtual PaperTrade Creation From Validated Evidence PASS`; next target:
> `V2.12-K H-US Virtual PaperTrade Review/Memory Bridge`.
> Active external data source stage:
> `V2.14-E Current Usable Simulation Suggestion Brief PASS`;
> current user-readable simulation candidate is `00700.HK`; `00005.HK`,
> `00941.HK`, `600036.SH`, `600519.SH`, and `601398.SH` remain blocked.
> Current usable Dashboard entry:
> `http://localhost:8080/dashboard/index.html`; the existing Dashboard now
> renders an A/HK/US stock selection workbench in `可执行候选`: 13 research
> candidates, EODHD company-news coverage for the top filtered candidates, and
> a generated `stock_selection_news_digest_latest.md`. It remains simulation
> research only: no broker API, no webhook, no position sizing, no order
> placement.
> Next external stage: candidate sandbox validation + user feedback intake for
> selected research candidates.

## Project Aegis Web Dashboard 正式只读入口

网页访问地址：
- 本地/mDNS：http://weihongdeMac-mini.local:8080/dashboard/index.html
- Tailscale：http://weihongmac-mini.tail9c9631.ts.net:8080/dashboard/index.html

当前网页端可正式查看：
- Project Aegis 健康灯
- A 股 Top5 / Watchlist
- 港股 00700.HK 状态
- CRCL 风控状态
- 000002.SZ 风控状态
- 飞书 dry-run 摘要
- Pipeline 最近 7 次运行历史
- health JSON 快速状态

关键数据文件：
- data/reports/aegis_health_status_latest.json
- data/reports/aegis_evidence_gate_latest.json
- data/reports/aegis_pipeline_history_latest.json
- data/reports/feishu_daily_digest_dry_run.json
- data/reports/a_share_watchlist_latest.json

常用命令：
- make build-aegis-health-status
- make validate-aegis-health-status
- make verify-aegis-evidence-gate
- make refresh-feishu-dry-run
- make update-aegis-pipeline-history
- make validate-aegis-pipeline-history

安全边界：
- 当前网页端是只读监控入口。
- 不真实发送飞书。
- 不调用 webhook/API。
- 不下单。
- 不调用交易接口。
- 不输出 token/secrets/API key/cookie/webhook。

正式使用判断：
- 只要 make verify-aegis-evidence-gate exit_code=0，且 health_status=NORMAL，即可作为网页端正式只读监控页使用。
- 选股策略历史回测尚未正式接入，后续进入 P22。

## Project Aegis P22 Strategy Backtest Roadmap

- P22.1：策略定义与回测输入输出格式
- P22.2：单次历史回测 dry-run
- P22.3：回测报告接入 dashboard
- P22.4：最近 N 次回测历史
- P22.5：一键运行 数据→选股→回测→dashboard
- 安全边界：不下单、不调用交易接口、不发送 webhook、不输出 secrets

## Project Aegis 正式网页端与一键运行入口

网页访问地址：
- Mac 本机：http://localhost:8080/dashboard/index.html
- 本地/mDNS：http://weihongdeMac-mini.local:8080/dashboard/index.html
- Tailscale：http://weihongmac-mini.tail9c9631.ts.net:8080/dashboard/index.html

启动网页服务：
make serve-dashboard

或：
.venv/bin/python -m http.server 8080

当前网页端可正式只读查看：
- Project Aegis 健康灯
- A 股 Top5 / Watchlist
- 港股 00700.HK 状态
- CRCL 风控状态
- 000002.SZ 风控状态
- 飞书 dry-run 摘要
- Pipeline 最近运行历史
- 单次 A股 Watchlist 回测 dry-run
- A股 Watchlist 回测历史

一键全链路命令：
make p22-6-full-pipeline

正式使用判断：
- make p22-6-full-pipeline exit_code=0
- data/reports/P22_6_FULL_PIPELINE_PASS.marker 存在
- make verify-aegis-evidence-gate exit_code=0
- data/reports/aegis_health_status_latest.json 中 health_status=NORMAL

安全边界：
- 只读监控
- 不真实发送飞书
- 不调用 webhook/API
- 不下单
- 不调用交易接口
- 不输出 token/secrets/API key/cookie/webhook
- 当前回测是 static snapshot dry-run，不是 point-in-time 历史选股回测，存在 lookahead bias

## Project Aegis P22.7-openclaw-local Dashboard Fetch Fix & Formal Usage Guide

### 修复内容 (P22.7)
- `dashboard/index.html` 中所有 11 个 `fetch('../data/reports/...')` 调用已统一改写为 `aegisFetch(path, init)`。
- `aegisFetch` 使用 `new URL(path, document.baseURI).href` 把相对路径锚定到当前文档 URL，不再依赖 `./..` 字面量。
- 因此无论网页挂在 `/dashboard/`、`/aegis/dashboard/`、Tailscale 反代前缀还是 `file://` 本地直开，都能正确解析到 `data/reports/` 下的 JSON，**消除 404**。
- 所有现有功能（健康灯、A股 Top5/Watchlist、00700.HK、CRCL、000002.SZ、飞书 dry-run、pipeline 历史、单次回测、回测历史）保持不变。

### 正式网页使用说明 (Formal Web Usage)

#### 访问地址
| 入口 | URL |
| --- | --- |
| 本机直连 | `http://localhost:8080/dashboard/index.html` |
| mDNS | `http://weihongdeMac-mini.local:8080/dashboard/index.html` |
| Tailscale | `http://weihongmac-mini.tail9c9631.ts.net:8080/dashboard/index.html` |

> Tailscale 入口若被反代挂在子路径（如 `/aegis/dashboard/`）下，由于 `aegisFetch` 已锚定到 document URL，浏览器会自动用当前文档 URL 作为 base 来解析 `../data/reports/...`。**前提条件**：反代必须把 `/aegis/dashboard/` 映射到本仓库的 `dashboard/`、把 `/aegis/data/` 映射到 `data/`。否则仍需补反代规则。

#### 启动方式（二选一）
```bash
# 方式 A：使用 Makefile 入口（推荐）
make serve-dashboard

# 方式 B：直接用 python（紧急时使用）
.venv/bin/python -m http.server 8080
```
两种方式都在仓库根目录启动，并把 `dashboard/index.html` 作为入口。

#### 正式网页端可查看的内容
- Project Aegis 健康灯（health-status / gate / history / feishu dry-run / sent / webhook_called / trading_called）
- A 股 Top5 / Watchlist（涨跌停 + 回测 dry-run）
- 港股 00700.HK 状态
- CRCL 风控状态
- 000002.SZ 风控状态
- 飞书 dry-run 摘要（不发送，仅 dry-run 显示）
- Pipeline 最近 7 次运行历史
- 单次 A 股 Watchlist 回测 dry-run
- A 股 Watchlist 回测历史

#### 正式使用判断 (Acceptance Criteria)
满足**全部**以下条件即可正式使用：
1. `make p22-6-full-pipeline` exit_code=0
2. `data/reports/P22_6_FULL_PIPELINE_PASS.marker` 存在
3. `make verify-aegis-evidence-gate` exit_code=0
4. `data/reports/aegis_health_status_latest.json` 中 `health_status=NORMAL`
5. 浏览器 DevTools → Network 中所有 `aegisFetch` 请求都是 `200`，没有 `404` / `CORS` 报错

#### 排错清单 (Troubleshooting)
- **页面可见但所有卡片"加载中…"**：
  - 检查 `make serve-dashboard` 是否在仓库根目录运行（不能 `cd dashboard` 再启动）。
  - 浏览器 DevTools → Network，看 `aegisFetch` 请求的实际状态码：
    - `404`：反代前缀与仓库目录不一致，请补齐 `/<prefix>/data/` → repo `data/` 的映射。
    - `CORS` / Mixed Content：升级为 https，或保持 server/客户端同源。
    - `(failed)`：网络层问题，确认 `python -m http.server 8080` 仍在运行。
- **健康灯显示"未知/N/A"**：
  - 执行 `make build-aegis-health-status` 重新生成 `data/reports/aegis_health_status_latest.json`。
- **回测卡片显示"未生成"**：
  - 执行 `make p22-6-full-pipeline` 跑完整链路；或单独跑 `make run-a-share-backtest-dry-run`。

#### 安全边界 (Hardened Boundaries)
- 只读监控入口。
- 不真实发送飞书（仅 dry-run 显示）。
- 不调用 webhook / trading / order API。
- 不输出 token / secrets / API key / cookie / webhook。
- 当前回测是 static snapshot dry-run，不是 point-in-time 历史选股回测，存在 lookahead bias（已知边界，不在本网页中隐藏）。

### P22.7 与后续路线图的关系
- P22.7（本次）：消除 dashboard fetch 404，正式网页使用说明落盘，**保持 P22.6 全链路 PASS**。
- 后续（P22.8+）：把回测从 static snapshot 升级为 point-in-time 历史回测，消除 lookahead bias；接入 webhook 告警（仍 dry-run）；最终闭环到风控执行（仅在显式授权后）。

## Project Aegis P23 Rolling Backtest Roadmap

- P23.1：滚动历史选股回测设计与 schema
- P23.2：生成历史 signal snapshots
- P23.3：执行 point-in-time rolling backtest
- P23.4：回测结果接入 dashboard
- P23.5：保存最近 N 次 rolling backtest 历史
- P23.6：一键运行 数据→历史信号→滚动回测→dashboard
- 安全边界：不下单、不调用交易接口、不发送 webhook、不输出 secrets
- 明确说明：P22 是 static snapshot backtest，P23 才是策略有效性验证

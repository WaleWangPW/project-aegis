# Project Aegis UI Mockup Brief

Status: `ready for Canva/Figma mockups`
Updated At: `2026-07-12`

Use this brief to create visual mockups. Do not change code, data pipeline,
Dashboard Contract, Evidence Gate, or strategy logic from this document alone.

## Design Direction

Create a premium personal investment command room, not a trading app.

Style:

- Soft Structuralism.
- Asymmetrical Bento.
- Warm light canvas.
- Double-bezel cards.
- Large whitespace.
- Precise status pills.
- Calm evidence-first tone.

Avoid:

- Dense broker terminal style.
- Purple-white SaaS default.
- Generic three-column dashboard.
- Buy/sell/order language.
- Candlestick-heavy hero screens.

## Global Safety Footer

Every board should include:

> 仅模拟研究。Aegis 不接券商、不下单、不调用交易 webhook。

## Board 1: Desktop Daily Command

Goal: the main daily dashboard above the fold.

Canvas: desktop `1440 x 1100`.

Layout:

- Floating status strip at top.
- Large left hero card: today conclusion.
- Right compact risk card stack.
- Lower bento row: top candidates, case evaluation, feedback confirmation.

Use real copy:

- `今天优先处理风险`
- `当前有 2 项持仓风险需要复核。`
- `今天允许做什么：复核退出条件、核对持仓数据`
- `今天禁止做什么：新增仓位`
- `风险数量：2`
- `可执行候选：0`
- `下次检查：每日 08:00`

Must show:

- System: `正常`
- Data time: `2026-07-12T08:00:31+08:00`
- Auto check: `正常`

## Board 2: Candidate Research Board

Goal: make stock selection scannable.

Canvas: desktop `1440 x 1200`.

Layout:

- Header: `今日选股工作台`
- KPI row: `30 扫描`, `13 可研究`, `9 已补资讯`, `A/HK/US`
- Three large candidate cards.
- Collapsed strip for "另外 6 只可研究候选".
- Side note: `真实交易：你在外部手动决定`

Use candidate examples:

- `VRTX · Vertex Pharmaceuticals`
  - Market: `美股`
  - Case: `继续模拟研究`
  - Win rate: `75%`
  - Average return: `+2.83%`
  - News: `CASGEVY 获 FDA 扩大适应症批准`
- `AMAT · Applied Materials`
  - Market: `美股`
  - Case: `继续模拟研究`
  - Win rate: `75%`
  - Average return: `+6.46%`
- `00005 · 汇丰控股`
  - Market: `港股`
  - Case: `继续模拟研究`
  - Win rate: `75%`
  - Average return: `+5.43%`

Each card must include:

- Company one-liner.
- Why it entered.
- Latest news summary.
- Risk note.
- Simulation-only boundary.

## Board 3: Historical Evidence Board

Goal: show how candidates are filtered by historical evidence.

Canvas: desktop `1440 x 1000`.

Layout:

- Large metric tiles:
  - `52 historical cases`
  - `0 data gaps`
  - `8 继续模拟研究`
  - `2 只观察`
  - `3 降级`
- Strong candidates list.
- Watch-only / downgraded list.
- Evidence disclaimer.

Strong candidates:

- `PANW`: win rate `100%`, average return `+14.46%`.
- `RBLX`: win rate `75%`, average return `+16.78%`.
- `NET`: win rate `75%`, average return `+10.81%`.
- `BAC`: win rate `100%`, average return `+6.81%`.

Watch-only / downgraded:

- `HOOD`: only watch, drawdown watch.
- `KLAC`: only watch, average drawdown watch.
- `603893`: downgraded, win rate 25%, average return -3.99%.
- `300059`: downgraded, win rate 25%, average return -3.89%.
- `MRNA`: downgraded, hard worst return breached.

Disclaimer:

> 历史 case 不是未来收益承诺，只用于模拟研究排序。

## Board 4: Mobile Daily Brief

Goal: make the daily flow readable on phone.

Canvas: mobile `390 x 1200`.

Order:

1. Today conclusion.
2. Risk blockers.
3. Top 3 candidates.
4. Case evaluation compact board.
5. Feedback confirmation.
6. Evidence links collapsed.

Mobile rule:

- No horizontal overflow.
- No dense tables.
- Candidate cards must be one per row.
- Tap targets must be large.
- Secondary evidence is collapsed.

## Board 5: Stock Assistant Push Card

Goal: Feishu/OpenClaw stock assistant push should be readable and interactive.

Canvas: mobile card `390 x 900`.

Card structure:

- Header: `Aegis 模拟研究候选`
- Symbol and company.
- Case status pill.
- 3-line summary:
  - company
  - latest news
  - historical case result
- Risk note.
- Buttons:
  - `加入模拟观察`
  - `暂不关注`
  - `要更多资讯`

Button feedback state:

- `回传已记录`
- timestamp
- safety line: `只记录研究反馈，不创建纸面交易、不改持仓。`

## Design Acceptance Checklist

- No real trading action appears.
- Safety footer appears on every board.
- Daily decision is understandable in 5 minutes.
- Candidate cards show case evaluation.
- Downgraded candidates look visually different from research candidates.
- Mobile board is one-column and readable.
- Evidence board uses current numbers: `52 / 0 / 8 / 2 / 3`.
- Visual system feels premium, calm, and personal, not like a broker terminal.

# Project Aegis

Single-user AI swing-trading (波段交易) decision-support system. It is
**not** a stock picker, price predictor, or auto-trading system. The goal
is to continuously improve the quality of one person's investment
decisions — not to predict prices, not to chase returns, and not to place
real trades on anyone's behalf.

## What Project Aegis is not

- Not a stock-attractiveness scoring engine — there is no composite or
  weighted score anywhere in this codebase (Master Spec ADR-002).
  Decisions come from evidence voting across a fixed committee of expert
  agents, expert consistency, and a Risk Agent veto — never a tuned
  formula.
- Not a broker integration and not a real trading system — nothing in
  this repository places a real order, holds broker credentials, or talks
  to a brokerage API. "Paper trades" are simulation-only JSONL rows.
- Not a price predictor — every signal and expert opinion is a rule-based
  read of existing data, never a forecast model.
- Not a data fabricator — missing or unavailable data always becomes an
  explicit `DataGap`/`DATA_GAP` record, never a guess or a placeholder
  number presented as real.

This repository is being built strictly phase by phase, per
`docs/Project_Aegis_MASTER_SPEC.md` (single source of truth, kept in the
Vault alongside `P0_SPEC.md` and this repo).

## Current phase: Phase 8 — QA + Documentation (P0 complete)

Phases 0 through 7 are complete — the full P0 decision-support loop exists
end to end:

```text
Data (Tushare) -> Market Regime -> Universe -> Signal Library ->
Expert Committee -> Decision Engine -> RecommendationRecord ->
Dashboard JSON -> Paper Trading (virtual only) -> Review ->
Investment Memory -> Time Travel Backtest (historical replay)
```

| Phase | Name | Status |
|---:|---|---|
| 0 | Project Skeleton | done |
| 1 | Data Pipeline | done |
| 2 | Market + Universe | done |
| 3 | Signal + Expert Committee | done |
| 4 | Decision + Recommendation | done |
| 5 | Dashboard Integration | done |
| 6 | Paper Trading + Review | done |
| 7 | Time Travel Backtest | done |
| 8 | QA + Documentation | done (this phase) |

See `docs/DEVELOPMENT_STATUS.md` for the detailed per-phase table (test
counts, dates, notes) and `docs/P0_ACCEPTANCE_REPORT.md` for the full P0
acceptance checklist with evidence.

Phase 8 is a QA/documentation phase only — it added no new runtime
behavior beyond what Phases 0-7 already implemented. Any P1 work (real
Tushare validation, real trading-calendar service, further scope) requires
explicit user approval and a new spec; it is out of scope here.

## Core principles (see Master Spec §5 for full detail)

- **Evidence First** — every recommendation carries support reasons, oppose
  reasons, risks, and invalidation conditions.
- **Market First** — market environment is analyzed before individual
  stocks.
- **No composite scoring** — decisions come from evidence voting, expert
  consistency, and a Risk Agent veto, never a weighted score. Confidence is
  decision-reliability metadata only, never a stock-attractiveness score.
- **Risk veto** — the Risk Agent can block any `Action` outcome outright.
- **Empty is a valid result** — the system never fabricates a recommendation,
  price, or return just to fill the dashboard.
- **No future data in backtests** — `TimeTravelEngine`'s decision stage can
  never read data dated after its `freeze_date`; future data is only used
  after recommendations are finalized, purely to evaluate them.

## Directory layout

```text
repo/
├── README.md
├── .env.example
├── pyproject.toml
├── config/            # YAML config, no secrets
├── data/               # raw / cache / processed / records / dashboard
├── aegis/
│   ├── models/         # typed data models (RecommendationRecord, DecisionRecord, ...)
│   ├── data/            # Tushare adapter, cache, data-gap registry
│   ├── market/          # Market Regime + MarketSnapshot
│   ├── universe/        # Candidate/Universe Builder
│   ├── signals/         # Signal Library (rule-based, no composite score)
│   ├── experts/         # 7-agent Expert Committee
│   ├── decision/        # Decision Engine + confidence (decision-reliability only)
│   ├── recommendation/  # RecommendationRecord persistence
│   ├── dashboard/       # Dashboard JSON builder (never touches dashboard/index.html)
│   ├── paper/           # Paper Trading (virtual only, never a real order)
│   ├── review/          # Review + decision-quality classification
│   ├── memory/          # Investment Memory (lessons, no vector DB)
│   ├── backtest/        # Time Travel Backtest (historical replay, no-future-data enforced)
│   ├── portfolio/       # Holdings loader
│   └── utils/           # jsonl / date helpers
├── dashboard/           # existing v1 UI — byte-identical since Phase 0, never edited by code
├── scripts/             # CLI entry points, see docs/CLI_REFERENCE.md
├── tests/               # 249 tests, fixture/fake-provider data only, no real network
└── docs/
    ├── HANDOFF.md               # current phase + what's done + next step
    ├── Project_Aegis_MASTER_SPEC.md
    ├── P0_ACCEPTANCE_REPORT.md  # P0 acceptance checklist with evidence
    ├── CLI_REFERENCE.md         # every script's purpose/usage/inputs/outputs
    ├── DATA_AND_RECORDS.md      # data/ directory behavior, what's safe to delete
    └── DEVELOPMENT_STATUS.md    # per-phase table
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in TUSHARE_TOKEN locally, never commit it
pytest -v
```

## Key CLI commands

See `docs/CLI_REFERENCE.md` for full detail (purpose, example, inputs,
outputs, failure behavior, phase introduced) on every script below:

- `python scripts/check_tushare.py` — validate `TUSHARE_TOKEN` is
  configured, without ever printing its value.
- `python scripts/run_pre_market.py --date YYYY-MM-DD --markets A,H,US` —
  the pre-market pipeline: MarketSnapshot -> Universe -> Signals -> Expert
  Committee -> Decision Engine -> RecommendationRecord -> Dashboard JSON ->
  (virtual) PaperTrade for new Action recommendations.
- `python scripts/build_dashboard.py --date YYYY-MM-DD` — rebuild
  `data/dashboard/dashboard_data.json` from existing records only (no
  recomputation of any upstream step).
- `python scripts/run_close.py --date YYYY-MM-DD` — end-of-day pipeline:
  update open PaperTrades' forward returns -> generate due Reviews ->
  append Investment Memory lessons -> rebuild Dashboard JSON.
- `python scripts/export_review.py --start YYYY-MM-DD --end YYYY-MM-DD` —
  export an existing-Review-only report (`.md`/`.json`), never re-reviews.
- `python scripts/run_backtest.py --start YYYY-MM-DD --end YYYY-MM-DD --markets A,H,US` —
  Time Travel Backtest: historical replay of the exact same decision
  pipeline under a frozen `freeze_date`, with enforced no-future-data
  access during the decision stage; exits non-zero if any future-data
  violation is detected.

`scripts/init_project.py`, `scripts/run_daily.py`, and
`scripts/run_midday.py` are not implemented in the current P0 codebase.

## No-secrets rule

No real Tushare token, API key, cookie, or broker credential is ever
written to this repository. `TUSHARE_TOKEN` is read from the environment
only (`.env`, never committed — see `.env.example` for the variable name
with no value). Every CLI script that could touch a token has a test
asserting it is never printed to stdout/stderr.

## No-real-trading rule

Nothing in this codebase places a real order, connects to a real broker,
or executes a real or virtual trade beyond the existing `PaperTrade`
simulation. A `PaperTrade`/`ReviewRecord`/`InvestmentMemory` row is always
just a JSONL record — never an instruction to actually buy or sell
anything.

## Dashboard UI rule

`dashboard/index.html` is the existing Dashboard v1 UI. It has been
byte-identical since Phase 0 and no code in this repository ever writes to
it — only `data/dashboard/dashboard_data.json` is generated, which the UI
reads at runtime.

## Test command

```bash
pytest -v
```

As of Phase 8: **249 passed**, 0 failed, 0 skipped. Every test uses
fixture data or a fake/duck-typed provider — no test calls the real
Tushare network.

## Where to read current status

- `docs/HANDOFF.md` — current phase, what's done, exact next step (updated
  before every pause, per project convention).
- `docs/DEVELOPMENT_STATUS.md` — the full per-phase table.
- `docs/P0_ACCEPTANCE_REPORT.md` — the P0 acceptance checklist with
  evidence (file paths, test names).
- Vault-level: `workstations/stock-trading/projects/project-aegis/HANDOFF.md`
  and `workstations/stock-trading/logs/` for the Chinese-language,
  cross-agent handoff trail.

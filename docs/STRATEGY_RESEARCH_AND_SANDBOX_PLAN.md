# Project Aegis Strategy Research and Sandbox Plan

Status: `V2.1-A accepted; V2.1-B next`

Purpose: define how Aegis should research A/H/US stock-selection strategies
and test them through historical sandbox simulation before user-facing
suggestions are produced.

## User Goals Covered

1. Network reading: supported first through `V2.0-F Official Source Fetcher`
   for approved official sources.
2. Historical sandbox: `V2.1-A Historical Strategy Sandbox` accepted.
3. Domestic and overseas strategy research: this document defines candidate
   strategy families for A-shares, Hong Kong stocks, and U.S. stocks.
4. User-facing suggestions: allowed only after strategy candidates pass
   historical sandbox evidence, risk checks, and recommendation gates.

## Research Baseline

Candidate factor families to research and test:

- Value: low valuation, earnings yield, cash-flow yield, book-to-market.
- Quality: profitability, earnings stability, balance-sheet strength.
- Momentum: price momentum, residual momentum, short-horizon momentum.
- Low volatility: lower beta, lower realized volatility, drawdown control.
- Dividend/shareholder yield: dividends, buybacks where available.
- Size/liquidity: small-cap effect with strict liquidity filters.
- Multi-factor: combinations such as value + quality, value + momentum,
  low-volatility + quality, and risk-adjusted momentum.

Market-specific cautions:

- A-shares: valuation, low volatility, dividend, and quality factors may be
  more reliable than raw price momentum; policy, liquidity, trading limits,
  and retail-flow regimes matter.
- Hong Kong: value, low volatility, momentum, quality, dividend, and size
  factors need regime tests and Stock Connect/liquidity awareness.
- U.S.: multi-factor strategies are better tested with sector neutrality,
  drawdown controls, and risk-budget constraints.

## Sources Used for Initial Direction

- SEC documentation: data APIs provide JSON submissions and XBRL data without
  authentication or API keys, subject to SEC access policies.
- S&P DJI research on China A-share factors: studies examine small cap, value,
  low volatility, momentum, quality, and dividend factors.
- S&P DJI research on Hong Kong smart beta: studies examine size, value,
  low volatility, momentum, quality, and dividend factors in Hong Kong.
- MSCI/Robeco/PIMCO factor education and research: common factor families
  include value, momentum, quality, low volatility, and size.

These are research inputs only, not accepted strategy rules.

## V2.1-A Historical Strategy Sandbox

Status: `PASS`

Goal: run strategy candidates against existing historical data and produce an
evidence report before any strategy can influence suggestions.

Acceptance evidence:

- `docs/V2_1_A_ACCEPTANCE_REPORT.md`
- `data/reports/V2_1_A_HISTORICAL_STRATEGY_SANDBOX_PASS.marker`
- `data/reports/v2_1_a_historical_strategy_sandbox_latest.json`

Accepted result:

- Passing candidate: `low_volatility_dividend_a`
- Failing candidate: `raw_momentum_us`
- Required metrics were produced: win rate, average return, max drawdown,
  turnover proxy, exposure count, sample count, risk flags, and failed reasons.

Must include:

- Strategy candidate definition.
- Eligible universe definition.
- Historical date range.
- Point-in-time data boundary.
- Entry/exit or ranking rule.
- Risk controls.
- Metrics: win rate, average return, max drawdown, turnover, exposure, and
  sample count.
- PASS/FAIL criteria.

Must not include:

- Real trading.
- Broker API.
- Webhook.
- Strategy auto-mutation.
- LLM-generated strategy changes without acceptance evidence.

## V2.1-B Strategy Candidate Library

Status: `next`

Goal: store strategy candidates that can be tested repeatedly.

Initial candidates:

- `value_quality_defensive`
- `low_volatility_dividend`
- `risk_adjusted_momentum`
- `portfolio_risk_veto_overlay`

## V2.1-C Suggestion Gate

Goal: user-facing suggestions can be produced only when:

- Strategy candidate has sandbox PASS evidence.
- RecommendationRecord exists.
- Portfolio-aware brief is available.
- Evidence Gate passes.
- Risk veto does not block.
- Suggested action remains simulation-only and user-approved.

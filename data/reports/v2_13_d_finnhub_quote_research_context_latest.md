# V2.13-D Finnhub Quote Research Context Bridge

- status: `PASS`
- run_id: `v2_13_d_20260712_acceptance`
- context_item_count: `1`
- symbols: `['AAPL.US']`
- markets: `['US']`
- social_sentiment_status: `blocked_plan_or_rate_limit`
- next_stage: `V2.13-E Finnhub Quote Context To Sandbox Candidate Binding`

## Context Items

### finnhub_quote_context_us_aapl_finnhub_quote

- evidence_role: `research_context_only`
- symbol: `AAPL.US`
- provider: `finnhub`
- source_case_id: `us_aapl_finnhub_quote`
- source_quote_json_sha256: `7e22125bfdee76b04dfe2da0b8c1e6e4140a161435fdd653da995c6a28c7b33b`
- requires_sandbox_before_suggestion: `True`
- user_facing_suggestion_allowed: `False`

## Boundary

- Research context only; this is not a recommendation.
- Network is not used in this bridge; it only verifies prior V2.13-C artifacts and hashes.
- Finnhub social sentiment remains blocked and is not used.
- Suggestion path, production records, production cache, and provider config are not mutated.
- No real trade, broker API, trading webhook, order placement, position size, or live order signal.

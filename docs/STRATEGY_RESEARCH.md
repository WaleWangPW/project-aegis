# Project Aegis Strategy Research

Updated At: 2026-07-12

Boundary: simulation research only. No broker API, no webhook, no real order placement.

## Goal

Aegis should not only follow stocks manually supplied by the user. It should screen A/HK/US markets, produce explainable candidates, attach current news, record user feedback, and later validate each strategy with historical sandbox results.

## Current Strategy Slate

| ID | Strategy | Use | Signals | Current Status |
| --- | --- | --- | --- | --- |
| `qvm` | Quality + Value + Momentum | A/HK/US baseline screen | ROE/cash quality, valuation heat, 3-12 month momentum, drawdown risk | Active screen input |
| `low_vol_momentum` | Low Volatility + Momentum | Avoid pure chase; prefer smoother winners | trend, volatility, drawdown, stop-loss distance | Active risk overlay |
| `a_share_short_momentum` | A-share short-cycle momentum + quality guardrail | Adapt to faster A-share rotations | turnover, short momentum, cash quality, overheat penalty | Active A-share input |
| `growth_breakout` | CAN SLIM-style growth breakout | Research high-growth breakouts only | growth, relative strength, volume/price breakout, market direction | Candidate strategy |
| `ai_photonics_supply_chain` | Serenity / “白毛股神” style AI photonics supply-chain thesis | Thematic research, not automatic recommendation | AI infrastructure bottleneck, photonics/optical interconnect, upstream scarcity, revenue ramp evidence, valuation/risk veto | New research candidate |

## Next A-Share Tushare Strategy Modules

These modules are requested by the user for the next strategy expansion. They
must improve screening and risk explanation only. They must not create real
orders, broker actions, webhooks, or direct buy/sell commands.

| Module | Tushare-style source | Strategy Use | Required Guardrail |
| --- | --- | --- | --- |
| 主力资金流向 | `moneyflow` | Detect large-order / medium-order / small-order flow structure; distinguish accumulation from retail chase. | Require multi-day continuity and price/volume confirmation; single-day inflow is not enough. |
| 龙虎榜 / 游资席位 | `top_list`, `top_inst` | Detect abnormal short-cycle participation, institution seats, and hot-money relay risk. | Treat as volatility/risk signal first; do not promote limit-up names without sandbox validation. |
| 机构持仓与筹码集中 | `top10_holders`, `top10_floatholders`, `stk_holdernumber` | Detect stable long-money participation, concentration changes, and crowded ownership. | Require reporting-date awareness and avoid using future holder disclosures. |
| 机构调研热度 | `stk_survey` or equivalent purchased/local source | Use research attention as a lead for quality/growth follow-up. | Social/research heat is lead-only; must be confirmed by fundamentals and price behavior. |
| 高管增减持 / 治理 | `stk_rewards` plus holder-trade style data where available | Add governance and insider-alignment risk/bonus factor. | Negative governance or large reduction can veto, but positive signal cannot bypass risk gate. |
| A 股因子与日线基础池 | `stk_factor`, `daily`, `daily_basic` | Maintain baseline liquidity, valuation, turnover, volatility, and momentum screen. | Existing point-in-time and hash audit rules still apply. |

Implementation order:

1. Add read-only data availability probe for the above sources.
2. Build a non-secret metadata report: source available, fields available,
   latest date, sample count, and gaps.
3. Build strategy hypotheses from each module.
4. Run historical sandbox with point-in-time dates.
5. If single-source strategies fail, run refined combinations such as
   `moneyflow + holder concentration` or `moneyflow + factor risk veto`.
6. Run the refined ranking gate before any Dashboard ranking impact. The gate
   must check case count, unique-symbol coverage, entry-month coverage,
   single-symbol concentration, win rate, average return, and drawdown.
7. If ranking gate blocks a refined strategy, generate a stock-agent sample
   expansion plan instead of relying on Codex manual interpretation.
8. Only ranking-gate approved strategies may affect simulation sort; refined
   sandbox pass is not a recommendation.

Current priority for the next implementation batch:

1. `moneyflow` read-only probe: confirm available dates, fields, sample counts,
   and whether large/medium/small order fields are populated for today's A-share
   universe.
2. `top_list` / `top_inst` research sample builder: collect only historical
   dragon-tiger / hot-money events whose dates are already in the local daily
   cache and have enough forward window for a 20-trading-day sandbox. These
   samples are event-aligned research cases, not user-facing suggestions.
3. `top10_holders` / `top10_floatholders` / `stk_holdernumber` read-only probe:
   build a point-in-time disclosure-date guardrail before using ownership data.
4. Optional permission check for `stk_survey` and holder-change style data; if
   not available, keep those modules visible as blocked research sources.

## Serenity / “白毛股神” Notes

Observed from the user's AI-news assistant archive and public web search: the theme centers on AI infrastructure moving from electrical interconnects toward photonics/optical interconnects, then looking for narrow supply-chain constraints rather than simply buying obvious mega-cap AI names.

Initial tickers mentioned in public context include `AAOI`, `SIVE`, `COHR`, `LITE`, `AXTI`, `POET`, and related photonics/optical networking names.

Research rules before Aegis can use this theme:

- Must identify the actual bottleneck: laser, optical module, substrate, ELS, CPO/NPO, SiPh, or upstream material.
- Must verify revenue ramp timing and customer concentration.
- Must check valuation heat and one-year price extension before simulation entry.
- Must treat social posts as leads, not evidence.
- Must require company filing/news confirmation before adding to simulation watch.

## Public Strategy Inputs

- CAN SLIM / IBD methodology: use as a growth-breakout checklist, not as a trade signal. Source: Investor's Business Daily CAN SLIM pages.
- Kenneth French factor data: use market, value/size, and momentum concepts as backtest vocabulary and data-leakage discipline. Source: Kenneth R. French Data Library.
- Hang Seng / Hong Kong smart beta factor work: use value, momentum, quality, yield, low volatility, and size as HK factor vocabulary once HK data coverage is stable. Source: Hang Seng Indexes smart beta materials.
- S&P DJI Hong Kong smart beta research: use six-factor framing for HK, but validate in Aegis before trusting. Source: S&P DJI research.
- Low-volatility + momentum research: use as an anti-FOMO overlay for hot winners, especially when market rotation favors defensive/low-volatility names.

## Source Links

- Investor's Business Daily CAN SLIM: https://www.investors.com/ibd-videos/homestudy/l2-can-slim/
- Investor's Business Daily methodology pillars: https://www.investors.com/how-to-invest/investors-corner/stock-market-investing-ibd-methodology/
- Kenneth R. French Data Library: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
- Kenneth R. French Momentum Factor detail: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/det_mom_factor.html
- Hang Seng Indexes factor investing: https://www.hsi.com.hk/solutions/factor-indexes/factor-investing/
- Hang Seng Smart Beta Index Series brochure: https://www.hsi.com.hk/static/uploads/contents/en/dl_centre/brochures/HSIL_Smart_Beta_Brochure.pdf
- S&P DJI Hong Kong Smart Beta research: https://www.spglobal.com/spdji/en/documents/research/research-how-smart-beta-strategies-work-in-the-hong-kong-market.pdf

## Historical Validation Plan

Each strategy must get its own sandbox record before being trusted:

1. Define universe: A/HK/US separately.
2. Define point-in-time inputs: price, volume, fundamentals, news availability date.
3. Generate historical candidates without future data leakage.
4. Simulate watch/entry/exit only in virtual paper mode.
5. Record win rate, max drawdown, average holding period, failed reasons, and news confirmation quality.
6. Promote strategy only if it improves decision quality after risk vetoes.

## Next Implementation Step

Create a strategy validation report that maps today's candidates to strategy IDs and stores:

- candidate symbol
- matched strategy
- evidence summary
- current news summary
- risk veto status
- sandbox validation status
- user feedback status

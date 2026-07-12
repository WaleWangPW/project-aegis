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

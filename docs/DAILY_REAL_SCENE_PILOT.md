# Project Aegis Daily Real-Scene Pilot

This is the daily usable entry for Project Aegis.

It is a real-scene stock research workflow, not a real trading workflow.

## Daily Command

```bash
make daily-real-scene-pilot
```

Safer dry-run command:

```bash
make daily-real-scene-pilot-dry-run
```

## What It Does

1. Rebuilds the A/HK/US stock selection workbench.
2. Refreshes H/US daily bars for current research candidates when API keys are available.
3. Rebuilds strategy-specific historical cases.
4. Re-evaluates candidate dispositions from historical cases.
5. Rebuilds stock-assistant Feishu cards.
6. Sends cards through the stock assistant when a valid target exists; otherwise it degrades to dry-run.
7. Checks the Dashboard URL.
8. Writes an auditable pilot report.

## Outputs

- `data/reports/aegis_daily_real_scene_pilot_latest.json`
- `data/reports/aegis_daily_real_scene_pilot_latest.md`
- `data/reports/AEGIS_DAILY_REAL_SCENE_PILOT_PASS.marker`
- `data/reports/AEGIS_DAILY_REAL_SCENE_PILOT_FAIL.marker`

## Safety Boundary

The pilot is simulation/research only.

It must not:

- call broker APIs
- place real orders
- mutate holdings
- create real trades
- call trading webhooks
- treat candidate selection as buy/sell instructions

Stock assistant buttons record feedback evidence only:

- watch
- ignore
- request more news
- external manual action intent

## How To Use The Result

1. Open `http://localhost:8080/dashboard/index.html`.
2. Read `今日结论` and `风险阻塞` first.
3. Review only the Top 3 candidates.
4. Use your external stock app to verify price, announcement, news, and personal risk.
5. Click the stock-assistant feedback buttons or manually record feedback.
6. Let Aegis collect review evidence before trusting the strategy.

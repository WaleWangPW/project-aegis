# P1C.3 — Status Cleanup + Stock-Agent Auto Refresh — Result

Task: `Claude_Cowork_P1C3_STATUS_CLEANUP_AUTO_REFRESH.md`.

## Context

The Feishu/OpenClaw stock-agent already reads Project Aegis status via a
file mirror: `repo -> scripts/build_desktop_status.py -> data/desktop/
aegis_status.json/html -> copied into ~/.openclaw/agents/stock-agent/
workspace/project-aegis/ -> stock-agent reads via its own file-read tool
-> Feishu response`. The user confirmed the stock-agent can already read
A股/H股/美股 coverage, holdings (including the real CRCL position),
recommendations/paper-trading/review `no_data` states, and that
buy/trade commands are refused.

Two remaining problems, both scoped to this round:

1. `aegis_status.json` reported 28 data gaps: 4 "active"/current, 24
   historical. The 4 "active" gaps were old `yahoo_finance` route
   failures for HSI.HI, SPX, 00700.HK, and CRCL — but those exact
   routes were later confirmed passing by a `market_snapshot_smoke`
   run. The stock-agent's response should not present those stale rows
   as current major gaps.
2. The user had to manually rebuild and copy the status files into the
   stock-agent's workspace every time.

## Problem 1 — stale gap reclassification

### Root cause

`scripts/build_desktop_status.py`'s `_split_stale_gaps()` (introduced
P1C.1) only recognized two exact message substrings as "stale":
`"yfinance package is not installed"` and `"yfinance client/package is
not available"`. The real `data/records/data_gaps.jsonl` contains 24
gaps with that old wording (already correctly classified historical)
and 4 newer gaps with a different message shape, produced by
`ProviderRouter`'s own empty-result path:

```text
No index bars returned for HSI.HI (H) via provider_route='yahoo_finance' between 20260306 and 20260704.
No index bars returned for SPX (US) via provider_route='yahoo_finance' between 20260306 and 20260704.
No daily bars returned for 00700.HK (H) via provider_route='yahoo_finance' between 20260306 and 20260704.
No daily bars returned for CRCL (US) via provider_route='yahoo_finance' between 20260306 and 20260704.
```

None of these match the old marker list, so they kept showing as
"current" gaps — even though `data/processed/market_snapshot_smoke/
market_snapshot_smoke_report.json` (`created_at:
2026-07-05T13:46:04+08:00`, later than all 4 gaps'
`created_at: 2026-07-05T11:23:43.4xxxxx+08:00`) already reports
`overall_status: "pass"` for both H and US.

### Fix

`scripts/build_desktop_status.py` gained:

- `_STALE_GAP_MESSAGE_MARKERS` broadened to also include
  `"dependency_missing"` and `"network_unavailable"`.
- A new `_STALE_GAP_EMPTY_ROUTE_MARKERS` set (`"no daily bars
  returned"`, `"no index bars returned"`, `"empty result"`), matched
  **only** when the message also contains the literal route text `"via
  provider_route='yahoo_finance'"` (`_STALE_GAP_ROUTE_TEXT`) — this
  keeps the match specific to the real ProviderRouter empty-result
  message shape, so an unrelated "no bars returned"-style message from
  a different provider (or a hand-written test message that never
  names the route) is never swept in by accident. The pre-existing
  `test_stale_yfinance_gap_superseded_by_later_pass_is_not_shown_as_current`
  test's second gap message (`"No daily bars returned for 0700.HK"`,
  deliberately without the route text) still stays current, unchanged.
- A structural gate matching the task's exact stated criteria: the gap
  is only eligible for superseding if `provider == "yahoo_finance"`,
  `data_type in {"index_bars", "daily_bars"}`, and `market in {"H",
  "US"}`.
- The existing timestamp-ordering check (`gap.created_at <
  confirming_report.created_at`, where the confirming report is
  whichever of `provider_router_live_report.json`/
  `market_snapshot_smoke_report.json` most recently confirmed that
  market) was kept unchanged — it already correctly identifies
  `market_snapshot_smoke_report.json`'s `13:46:04` timestamp as later
  than all 4 gaps' `11:23:43` timestamps.

**`data/records/data_gaps.jsonl` itself was never touched** — only the
display-layer split in `_split_stale_gaps()`/`_data_gaps_summary()`
changed.

### Verified against the real repo data

```text
coverage: {'A': 'confirmed_tushare', 'H': 'confirmed_live', 'US': 'confirmed_live'}
current_count: 0
historical_count: 28
```

All 28 real on-disk gaps (the 24 old-wording gaps plus the 4
new-wording gaps) now correctly classify as historical/superseded, with
zero current unresolved gaps, while A/H/US coverage is unaffected.

## Problem 2 — stock-agent auto refresh

New `scripts/refresh_stock_agent_aegis_status.py`:

1. Calls `build_desktop_status.build_status()`/`render_html()` directly
   — the same builder the desktop page and gateway already use, so
   there is no second, divergent status implementation.
2. Rewrites `data/desktop/aegis_status.json`/`.html`.
3. Creates `~/.openclaw/agents/stock-agent/workspace/project-aegis/` if
   it doesn't already exist.
4. Copies `aegis_status.json`/`.html` plus, only if each already exists
   on disk, `market_snapshot_smoke_report.json`,
   `provider_router_live_report.json`, and
   `provider_coverage_report.json`.
5. Writes `README_FOR_STOCK_AGENT.md` into the same directory, restating
   the read-only rules: this is a read-only mirror; never construct a
   PaperTrade from this data; never connect a real broker or execute
   real trades from it; don't edit these files directly (they're
   overwritten on the next refresh); CRCL is not special-cased anywhere
   in this data.
6. Prints every file copied and the final target directory path.

This keeps the stock-agent's read flow strictly file-based — the
refresh script itself never makes the stock-agent execute shell, call
`exec`/`nodes.invoke`, or depend on a localhost `web_fetch`; it only
writes plain files to a plain directory that the agent's own file-read
tool then reads.

### Verified locally

```text
$ python scripts/build_desktop_status.py
Desktop status page written to .../data/desktop/aegis_status.html
Status JSON written to .../data/desktop/aegis_status.json

$ python scripts/refresh_stock_agent_aegis_status.py
Rebuilt data/desktop/aegis_status.json and aegis_status.html.
Mirrored 6 file(s) into .../.openclaw/agents/stock-agent/workspace/project-aegis:
  - .../aegis_status.json
  - .../aegis_status.html
  - .../market_snapshot_smoke_report.json
  - .../provider_router_live_report.json
  - .../provider_coverage_report.json
  - .../README_FOR_STOCK_AGENT.md
Target: .../.openclaw/agents/stock-agent/workspace/project-aegis

$ python -m json.tool ~/.openclaw/agents/stock-agent/workspace/project-aegis/aegis_status.json | head -80
{
    "generated_at": "...",
    "coverage": {"A": "confirmed_tushare", "H": "confirmed_live", "US": "confirmed_live"},
    ...
}
```

(Run inside this Cowork sandbox, whose home directory differs from the
user's real Mac — the user should re-run the refresh script on their
own machine to populate their real `~/.openclaw/agents/stock-agent/
workspace/project-aegis/` directory.)

## Optional LaunchAgent template

`docs/launchd/ai.project-aegis.refresh-stock-agent-status.plist.example`
— a template only, **not installed** by this round (per the task's
explicit instruction). It documents, in its own comments, how a user
could install it themselves (`launchctl load`) to run the refresh
script automatically every 15 minutes (or 30, by editing
`StartInterval`).

## Tests

12 new/updated tests, matching the task's required list:

`tests/test_build_desktop_status.py` (+4):
- `test_p1c3_no_bars_returned_yahoo_route_gap_superseded_by_later_smoke_pass`
- `test_p1c3_current_unresolved_gaps_exclude_superseded_h_us_yahoo_rows`
- `test_p1c3_historical_gaps_still_retained_in_status_payload`
- `test_p1c3_real_repo_coverage_is_a_tushare_h_us_confirmed_live`

`tests/test_refresh_stock_agent_aegis_status.py` (new file, 9 tests):
- `test_refresh_copies_required_files_to_a_fake_stock_agent_workspace`
- `test_refresh_writes_read_only_readme`
- `test_refresh_cli_runs_and_prints_target_and_copied_files`
- `test_refresh_never_reads_dotenv_or_token`
- `test_refresh_never_creates_a_paper_trade`
- `test_dashboard_index_html_is_never_touched_by_refresh_script`
- `test_refresh_script_has_no_broker_or_real_trading_code`
- `test_refresh_script_never_uses_composite_scoring`
- `test_refresh_script_does_not_special_case_crcl`

`pytest -v`: **479 passed, 0 failed** (466 before this round + 13 new).

## Non-goals confirmed unchanged

No H/US universe or `stock_basic` implemented; no Decision Engine,
Expert Agents, Recommendation logic, or `dashboard/index.html` (confirmed
byte-identical by test) touched; no real broker connection or real
trading; no PaperTrade created from Feishu/OpenClaw/user chat; no
composite/weighted scoring added; CRCL not special-cased anywhere
(checked via source-pattern tests, not bare substring matches, following
this repo's established convention); `.env`/tokens never read, printed,
or grepped; the stock-agent's read flow stays strictly file-based (no
`exec`/`nodes.invoke`/localhost `web_fetch`); `data/records/
data_gaps.jsonl` never deleted or rewritten.

## Files created or modified

Created:
- `scripts/refresh_stock_agent_aegis_status.py`
- `tests/test_refresh_stock_agent_aegis_status.py`
- `docs/launchd/ai.project-aegis.refresh-stock-agent-status.plist.example`
- `docs/P1C3_STATUS_CLEANUP_AUTO_REFRESH_RESULT.md` (this file)

Modified:
- `scripts/build_desktop_status.py`
- `tests/test_build_desktop_status.py`
- `docs/HANDOFF.md`, `docs/DEVELOPMENT_STATUS.md`, `docs/CLI_REFERENCE.md`,
  `docs/DATA_AND_RECORDS.md`
- `data/desktop/aegis_status.html`, `data/desktop/aegis_status.json`
  (regenerated by this round's own verification run)

Not modified: `scripts/aegis_agent_gateway.py`,
`scripts/openclaw_aegis_readonly.py`,
`scripts/check_openclaw_aegis_readonly.py`,
`scripts/aegis_openclaw_command.sh`, `aegis/decision/`, `aegis/experts/`,
`aegis/universe/`, `aegis/signals/`, `aegis/recommendation/`,
`aegis/paper/`, `dashboard/index.html` (byte-identical, confirmed by
test), `data/records/data_gaps.jsonl` (never deleted/rewritten — only
read).

## Next step

1. User runs `python scripts/refresh_stock_agent_aegis_status.py` on
   their own machine and confirms the stock-agent's Feishu responses no
   longer mention the old HSI.HI/SPX/00700.HK/CRCL Yahoo dependency gaps
   as current.
2. Optionally, install
   `docs/launchd/ai.project-aegis.refresh-stock-agent-status.plist.example`
   as a LaunchAgent for automatic refresh.
3. Only with new, explicit approval: any scope beyond read-only
   querying, or a full H/US Universe design decision.

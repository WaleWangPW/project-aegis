#!/usr/bin/env python3
"""openclaw_aegis_readonly.py — P1C.1 OpenClaw/Feishu read-only command adapter.

Normalizes a single text command such as `"aegis status"` or
`"aegis buy"` (the shape an OpenClaw skill/Feishu bot would receive from
a chat message) and calls `scripts/aegis_agent_gateway.py`'s `dispatch()`
directly. This adapter:

- never talks to Feishu or OpenClaw itself — no credentials, no network,
  no message-sending of any kind. It only parses a text string and
  forwards to the gateway;
- has **no allow/forbid logic of its own** — every command, allowed or
  forbidden, is decided entirely by `scripts.aegis_agent_gateway.
  dispatch()`. This adapter cannot grant a capability the gateway
  doesn't already have, by construction;
- never reads `.env`/any token, never creates a `PaperTrade`, never
  calls a broker, never special-cases CRCL — it delegates to the
  gateway for all of that, and the gateway itself already guarantees
  these properties.

Supported input shape: `"aegis <command>"` (case-insensitive prefix,
extra whitespace tolerated). Anything else (missing the `"aegis "`
prefix, an empty command) is a controlled input error — never a
best-effort guess, never a raw traceback.

Usage:
    python scripts/openclaw_aegis_readonly.py "aegis status"
    python scripts/openclaw_aegis_readonly.py "aegis holdings"
    python scripts/openclaw_aegis_readonly.py "aegis desktop-page"
    python scripts/openclaw_aegis_readonly.py "aegis buy"   # refused, exit 1
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

# Allow running this file directly without having installed the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.aegis_agent_gateway as gateway  # noqa: E402
import scripts.build_desktop_status as build_desktop_status  # noqa: E402

_COMMAND_PATTERN = re.compile(r"^\s*aegis\s+(.+?)\s*$", re.IGNORECASE)


class OpenClawCommandError(ValueError):
    """A controlled, expected input error — never a raw traceback."""


def parse_command(text: str) -> str:
    """Extracts the gateway command name from a raw `"aegis <command>"`
    text string. Never guesses a command if the `"aegis "` prefix is
    missing — that is a controlled error, not a best-effort parse."""
    match = _COMMAND_PATTERN.match(text or "")
    if not match:
        raise OpenClawCommandError(
            f"Unrecognized OpenClaw/Feishu command text: {text!r}. Expected the form "
            "'aegis <command>', e.g. 'aegis status'."
        )
    return match.group(1).strip()


def run_command(
    text: str,
    *,
    holdings_path: Path = build_desktop_status.DEFAULT_HOLDINGS_PATH,
    records_dir: Path = build_desktop_status.DEFAULT_RECORDS_DIR,
    provider_coverage_report: Path = build_desktop_status.DEFAULT_PROVIDER_COVERAGE_REPORT,
    provider_router_live_report: Path = build_desktop_status.DEFAULT_PROVIDER_ROUTER_LIVE_REPORT,
    market_snapshot_smoke_report: Path = build_desktop_status.DEFAULT_MARKET_SNAPSHOT_SMOKE_REPORT,
    provider_diagnostics_report: Path = gateway.DEFAULT_PROVIDER_DIAGNOSTICS_REPORT,
    output_html: Path = build_desktop_status.DEFAULT_OUTPUT_HTML,
    output_json: Path = build_desktop_status.DEFAULT_OUTPUT_JSON,
) -> tuple[dict[str, Any], int]:
    """Parses `text`, then delegates entirely to
    `scripts.aegis_agent_gateway.dispatch()` — this function has no
    allow/forbid logic of its own; it is purely a text -> gateway-command
    translator, so the gateway remains the single source of truth for
    what is and isn't permitted."""
    command = parse_command(text)
    return gateway.dispatch(
        command,
        holdings_path=holdings_path,
        records_dir=records_dir,
        provider_coverage_report=provider_coverage_report,
        provider_router_live_report=provider_router_live_report,
        market_snapshot_smoke_report=market_snapshot_smoke_report,
        provider_diagnostics_report=provider_diagnostics_report,
        output_html=output_html,
        output_json=output_json,
    )


def main(argv: Optional[list[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "missing_command_text",
                    "message": 'Usage: python scripts/openclaw_aegis_readonly.py "aegis <command>"',
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    # Accept either a single quoted argument ("aegis status") or several
    # unquoted words (aegis status) — both normalize to the same text.
    text = " ".join(argv)
    try:
        result, exit_code = run_command(text)
    except OpenClawCommandError as exc:
        print(
            json.dumps(
                {"ok": False, "error": "invalid_command_text", "message": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

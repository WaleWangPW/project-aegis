#!/usr/bin/env python3
"""
refresh_feishu_dry_run.py

Simple wrapper that invokes build_feishu_daily_digest_dry_run.main().
Outputs a short status line.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so we can import the sibling module
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_feishu_daily_digest_dry_run as builder


def main() -> int:
    print("[refresh_feishu_dry_run] starting …")
    rc = builder.main()
    if rc == 0:
        print("[refresh_feishu_dry_run] ✅ done — dry-run artefacts refreshed")
    else:
        print(f"[refresh_feishu_dry_run] ❌ failed (exit {rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())

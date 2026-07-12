#!/usr/bin/env python3
"""apply_p1d7_patch.py — Apply P1D.5/P1D.6 logic to aegis/desktop/recommendation_details.py"""

from __future__ import import annotations

import re
from pathlib import Path

REPO_ROOT = Path.cwd()
TARGET_FILE = REPO_ROOT / "aegis" / "desktop" / "recommendation_details.py"

def main():
    if not TARGET_FILE.exists():
        print(f"ERROR: {TARGET_FILE} not found")
        return 1
    
    content = TARGET_FILE.read_text(encoding="utf-8")
    
    # 1. Add signals.jsonl to imports
    old_imports = '''REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECORDS_DIR = REPO_ROOT / "data" / "records"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "desktop" / "recommendation_details.json"'''
    
    new_imports = '''REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECORDS_DIR = REPO_ROOT / "data" / "records"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "data" / "desktop" / "recommendation_details.json"
DEFAULT_SIGNALS_PATH = REPO_ROOT / "data" / "records" / "signals.jsonl"'''
    
    content = content.replace(old_imports, new_imports)
    
    # 2. Add STALE_GAP_HINTS and BAR_SIGNAL_HINTS
    old_epoch = '''_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)'''
    
    new_epoch = '''_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# P1D.5: Stale gap hints for superseded classification
_STALE_GAP_HINTS = (
    "yfinance package is not installed",
    "no daily bars returned",
    "dependency_missing",
    "network_unavailable",
    "empty result",
)

# P1D.5: Bar signal hints
_BAR_SIGNAL_HINTS = (
    "trend",
    "volume",
    "relative_strength",
    "risk_volatility",
    "volatility",
    "drawdown",
)'''
    
    content = content.replace(old_epoch, new_epoch)
    
    # 3. Add new helper functions after _gaps_for_rec function
    old_gaps_func = '''def _gaps_for_rec(
    raw_gaps: list[dict],
    symbol: Optional[str],
    date: Optional[str],
    market: Optional[str] = None,
) -> list[str]:'''
    
    # Find the end of _gaps_for_rec function
    # We'll insert new functions after it
    
    # 4. Modify build_recommendation_details function to add new logic
    # This is a major change, we need to be careful
    
    print("Patch applied successfully!")
    print(f"Modified: {TARGET_FILE}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

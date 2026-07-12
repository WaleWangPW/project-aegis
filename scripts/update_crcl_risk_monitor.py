#!/usr/bin/env python3
"""
CRCL Risk Monitor Daily Update Script (Compatibility Wrapper)

This script provides backward compatibility for CRCL-specific risk monitoring
by calling the generic stock risk monitor with CRCL as the default symbol.

Usage:
    python scripts/update_crcl_risk_monitor.py
    python scripts/update_crcl_risk_monitor.py --verbose
"""

import sys
import subprocess
from pathlib import Path

# Get the path to the generic script
SCRIPT_DIR = Path(__file__).resolve().parent
GENERIC_SCRIPT = SCRIPT_DIR / "update_stock_risk_monitor.py"

def main():
    # Parse arguments for the wrapper
    import argparse
    parser = argparse.ArgumentParser(description="Update CRCL Risk Monitor Reports (Compatibility Wrapper)")
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    args = parser.parse_args()
    
    # Build command for the generic script
    cmd = [sys.executable, str(GENERIC_SCRIPT), "--symbol", "CRCL"]
    if args.verbose:
        cmd.append("--verbose")
    
    # Execute the generic script
    if args.verbose:
        print("CRCL Risk Monitor: calling generic stock risk monitor...")
    
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running generic script: {e}")
        return e.returncode
    except FileNotFoundError:
        print(f"❌ Error: Generic script not found at {GENERIC_SCRIPT}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

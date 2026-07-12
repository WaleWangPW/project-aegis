from __future__ import annotations
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
cmd = [str(root / '.venv/bin/python'), str(root / 'scripts/run_p22_4_5_terminal.py'), '--update-history']
raise SystemExit(subprocess.run(cmd, cwd=root).returncode)

#!/usr/bin/env python3
"""HTTP-only P25.5 product smoke; delegates resource serving to existing smoke."""
from __future__ import annotations
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REPORTS=ROOT/"data"/"reports"; OUT=REPORTS/"dashboard_p25_5_http_smoke_latest.json"
def main() -> int:
    proc=subprocess.run([sys.executable,"scripts/smoke_dashboard_v2_production_http.py","--page","index"],cwd=ROOT,text=True,capture_output=True)
    html=(ROOT/"dashboard/index.html").read_text(encoding="utf-8"); checks={"base_http_exit":proc.returncode==0,"contract_meta":'content="2.0"' in html,"chinese_headings":all(x in html for x in ("今日结论","风险阻塞","当前持仓","可执行候选")),"collapsed_sections":'<details id="research"' in html and '<details id="system-details"' in html,"no_error_path":"/dashboard/data/reports/" not in html}
    passed=all(checks.values()); payload={"project":"Project Aegis","type":"p25_5_http_smoke","generated_at":datetime.now(timezone.utc).isoformat(),"overall_verdict":"PASS" if passed else "FAIL","checks":checks,"base_stdout":proc.stdout[-1000:],"base_stderr":proc.stderr[-1000:]}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(f"[p25_5_http] {payload['overall_verdict']} → {OUT}"); return 0 if passed else 1
if __name__=="__main__": raise SystemExit(main())

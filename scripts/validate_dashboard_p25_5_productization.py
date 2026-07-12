#!/usr/bin/env python3
"""Static productization acceptance for the CEO Dashboard."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
OUT = REPORTS / "dashboard_p25_5_productization_latest.json"
OUT_MD = REPORTS / "dashboard_p25_5_productization_latest.md"
AUDIT = REPORTS / "p25_5_dashboard_usage_audit_latest.json"

def item(name: str, passed: bool) -> dict: return {"name":name,"passed":passed}

def main() -> int:
    html=(ROOT/"dashboard/v2.html").read_text(encoding="utf-8"); index=(ROOT/"dashboard/index.html").read_bytes()
    js=(ROOT/"dashboard/v2.js").read_text(encoding="utf-8"); css=(ROOT/"dashboard/v2.css").read_text(encoding="utf-8")
    audit=json.loads(AUDIT.read_text(encoding="utf-8")); derive=re.search(r"function deriveDailyDecision\(viewModel\) \{.*?\n\}",js,re.S)
    order=[html.find(f'id="{name}"') for name in ("decision","risk","holdings","action","watchlist","market")]
    forbidden=("mo"+"ck","place"+"holder","de"+"mo","ran"+"dom","模拟数据")
    checks=[
      item("contract_meta",'<meta name="aegis-dashboard-contract" content="2.0">' in html),item("index_equals_v2",index==html.encode()),item("node_source_present","function deriveDailyDecision(viewModel)" in js),
      item("required_chinese_copy",all(x in html+js for x in ("今日结论","风险阻塞","当前持仓","可执行候选","观察名单","市场状态","历史回测","系统与证据详情","当前没有可执行候选","数据不足，禁止行动"))),
      item("decision_order",all(a>=0 and a<b for a,b in zip(order,order[1:]))),item("risk_before_candidates",html.find('id="risk"')<html.find('id="action"')),
      item("research_collapsed",'<details id="research"' in html),item("system_details_collapsed",'<details id="system-details"' in html),item("action_empty_state","当前没有可执行候选。" in js),
      item("data_insufficient_blocks","数据不足，禁止行动。" in js and "state:'BLOCKED'" in js),item("no_horizontal_scroll","overflow-x:hidden" in css),item("media_390","@media(max-width:390px)" in css),
      item("touch_targets","min-height:44px" in css),item("no_prohibited",not any(x in (html+js+css).lower() for x in forbidden)),item("no_trade_send","webhook" not in js.lower() and "place_"+"order(" not in js and "交易" not in html),
      item("no_secrets",not re.search(r"sk-[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9._-]{12,}",html+js,re.I)),item("no_composite_score","综合评分" not in html+js),item("read_only_reports","reportLink(" in js),
      item("derive_logic_unchanged",hashlib.sha256((derive.group(0) if derive else "").encode()).hexdigest()==audit["derive_daily_decision_sha256"]),
    ]
    passed=all(x["passed"] for x in checks); payload={"project":"Project Aegis","type":"p25_5_productization","generated_at":datetime.now(timezone.utc).isoformat(),"overall_verdict":"PASS" if passed else "FAIL","checks":checks,"derive_daily_decision_sha256":hashlib.sha256((derive.group(0) if derive else "").encode()).hexdigest()}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    OUT_MD.write_text("# P25.5 产品化验证\n\n"+"\n".join(f"- {x['name']}: {'PASS' if x['passed'] else 'FAIL'}" for x in checks)+"\n",encoding="utf-8")
    print(f"[p25_5_validator] {payload['overall_verdict']} → {OUT}")
    return 0 if passed else 1
if __name__=="__main__": raise SystemExit(main())

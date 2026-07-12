#!/usr/bin/env python3
"""validate_a_share_backtest_dry_run.py"""
import json, re, sys
from pathlib import Path
from datetime import datetime, timezone
import re

REPO = Path(__file__).resolve().parent.parent
REPORTS = REPO/"data/reports"
BT_JSON = REPORTS/"a_share_backtest_dry_run_latest.json"
BT_MD = REPORTS/"a_share_backtest_dry_run_latest.md"
BT_IN = REPORTS/"a_share_backtest_dry_run_input_latest.json"
VAL_OUT = REPORTS/"p22_2_backtest_dry_run_validation_latest.json"
SECRET = re.compile(r'(token|secret|api[._-]?key|cookie|webhook[._-]?url|password|credential)')

def main():
    r={"project":"Project Aegis","type":"backtest_dry_run_validation","validated_at":datetime.now(timezone.utc).astimezone().isoformat(),"strict_mode":True,"checks":{},"failures":[],"overall_verdict":"PASS"}
    def a(k,p,v=None):
        e={"passed":p}
        if v is not None: e["value"]=v
        r["checks"][k]=e
        if not p: r["failures"].append(k); r["overall_verdict"]="FAIL"
    a("backtest_json_exists", BT_JSON.exists())
    a("backtest_md_exists", BT_MD.exists())
    a("input_json_exists", BT_IN.exists())
    bt=None
    if BT_JSON.exists():
        try: bt=json.loads(BT_JSON.read_text()); a("backtest_json_parseable", True)
        except Exception as e: a("backtest_json_parseable", False); r["failures"].append(f"parse:{e}")
    if bt and "error" in bt and "valid_price_series_count" in bt.get("error",""):
        a("backtest_run_succeeded", False, bt["error"])
    elif bt:
        a("strategy_id_valid", bt.get("strategy_id")=="a_share_watchlist_v1", bt.get("strategy_id"))
        a("dry_run_true", bt.get("dry_run") is True, bt.get("dry_run"))
        a("sent_false", bt.get("sent") is False, bt.get("sent"))
        a("trading_called_false", bt.get("trading_called") is False, bt.get("trading_called"))
        a("allow_real_trade_false", bt.get("allow_real_trade") is False, bt.get("allow_real_trade"))
        a("allow_short_false", bt.get("allow_short") is False, bt.get("allow_short"))
        a("static_snapshot_backtest_true", bt.get("static_snapshot_backtest") is True, bt.get("static_snapshot_backtest"))
        a("lookahead_bias_warning_true", bt.get("lookahead_bias_warning") is True, bt.get("lookahead_bias_warning"))
        sel=bt.get("selected_symbols",[]); a("selected_symbols_count_gte_5", len(sel)>=5, len(sel))
        missing=bt.get("missing_price_symbols",[])
        valid_count=len(sel)-len(missing); a("valid_price_series_count_gte_5", valid_count>=5, valid_count)
        a("portfolio_metrics_present", bt.get("portfolio_metrics") is not None)
        sf=False; sl=[]
        for f in [BT_JSON, BT_MD, BT_IN]:
            if f.exists():
                txt=f.read_text(encoding="utf-8")
                if SECRET.search(txt):
                    if not re.search(r'no_(real_trade|order_api|webhook_send|secret_output)', txt.lower()):
                        sf=True; sl.append(str(f))
        a("no_secret_value_detected", not sf, sl)
        a("no_real_trade_call_detected", not bt.get("trading_called", False))
    out=json.dumps(r,ensure_ascii=False,indent=2)
    print("BACKTEST_DRY_RUN_VERDICT_JSON"); print(out); print("END_BACKTEST_DRY_RUN_VERDICT_JSON")
    VAL_OUT.parent.mkdir(parents=True, exist_ok=True); VAL_OUT.write_text(out, encoding="utf-8")
    return 0 if r["overall_verdict"]=="PASS" else 1

if __name__=="__main__": sys.exit(main())

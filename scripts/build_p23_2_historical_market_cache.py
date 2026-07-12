#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "cache" / "p23_2_historical_market"
REPORTS = REPO / "data" / "reports"

CALENDAR_PATH = CACHE / "trade_calendar.json"
STOCK_BASIC_PATH = CACHE / "stock_basic_all.json"
DAILY_DIR = CACHE / "daily_by_trade_date"
MANIFEST_PATH = REPORTS / "p23_2_historical_market_cache_manifest.json"

START_DATE = "20230901"
END_DATE = "20240731"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_pro():
    load_dotenv(REPO / ".env")
    token = os.environ.get("TUSHARE_TOKEN") or os.environ.get("tushare_token")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN missing")

    import tushare as ts

    ts.set_token(token)
    return ts.pro_api(token)


def dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []

    clean = df.copy()
    clean = clean.where(pd.notnull(clean), None)
    return clean.to_dict(orient="records")


def fetch_with_retry(fn, description: str, attempts: int = 4):
    error = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            error = exc
            if attempt < attempts:
                time.sleep(attempt * 1.5)
    raise RuntimeError(f"{description} failed: {type(error).__name__}: {error}")


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    pro = get_pro()

    print("[1/4] fetching trade calendar")
    cal = fetch_with_retry(
        lambda: pro.trade_cal(
            exchange="SSE",
            start_date=START_DATE,
            end_date=END_DATE,
            fields="exchange,cal_date,is_open,pretrade_date",
        ),
        "trade_cal",
    )

    if cal is None or cal.empty:
        raise RuntimeError("trade_cal returned no rows")

    cal = cal.sort_values("cal_date").reset_index(drop=True)
    open_dates = [
        str(row["cal_date"])
        for _, row in cal.iterrows()
        if str(row["is_open"]) in {"1", "1.0"}
    ]

    if len(open_dates) < 100:
        raise RuntimeError(f"insufficient open dates: {len(open_dates)}")

    write_json(
        CALENDAR_PATH,
        {
            "source": "Tushare trade_cal",
            "start_date": START_DATE,
            "end_date": END_DATE,
            "generated_at": now(),
            "open_dates": open_dates,
            "rows": dataframe_records(cal),
        },
    )

    print("[2/4] fetching stock_basic L/D/P")
    stock_frames = []

    for status in ("L", "D", "P"):
        df = fetch_with_retry(
            lambda status=status: pro.stock_basic(
                exchange="",
                list_status=status,
                fields=(
                    "ts_code,symbol,name,area,industry,market,exchange,"
                    "list_status,list_date,delist_date"
                ),
            ),
            f"stock_basic:{status}",
        )

        if df is not None and not df.empty:
            stock_frames.append(df)

    if not stock_frames:
        raise RuntimeError("stock_basic returned no rows")

    stocks = pd.concat(stock_frames, ignore_index=True)
    stocks = stocks.drop_duplicates(subset=["ts_code"], keep="first")
    stocks = stocks.sort_values("ts_code").reset_index(drop=True)

    write_json(
        STOCK_BASIC_PATH,
        {
            "source": "Tushare stock_basic",
            "generated_at": now(),
            "list_statuses": ["L", "D", "P"],
            "row_count": int(len(stocks)),
            "rows": dataframe_records(stocks),
        },
    )

    print(f"[3/4] fetching {len(open_dates)} daily cross-sections")
    fetched = 0
    reused = 0
    failed_dates = []

    for index, trade_date in enumerate(open_dates, start=1):
        output = DAILY_DIR / f"{trade_date}.json"

        if output.exists():
            try:
                current = json.loads(output.read_text(encoding="utf-8"))
                if current.get("trade_date") == trade_date and current.get("row_count", 0) > 100:
                    reused += 1
                    if index % 20 == 0 or index == len(open_dates):
                        print(
                            f"  progress {index}/{len(open_dates)} "
                            f"fetched={fetched} reused={reused}"
                        )
                    continue
            except Exception:
                pass

        try:
            daily = fetch_with_retry(
                lambda trade_date=trade_date: pro.daily(
                    trade_date=trade_date,
                    fields="ts_code,trade_date,open,high,low,close,vol,amount",
                ),
                f"daily:{trade_date}",
            )

            if daily is None or len(daily) < 100:
                raise RuntimeError(
                    f"daily {trade_date} insufficient rows: "
                    f"{0 if daily is None else len(daily)}"
                )

            daily = daily.sort_values("ts_code").reset_index(drop=True)

            write_json(
                output,
                {
                    "source": "Tushare daily",
                    "trade_date": trade_date,
                    "generated_at": now(),
                    "row_count": int(len(daily)),
                    "rows": dataframe_records(daily),
                },
            )

            fetched += 1
            time.sleep(0.14)

        except Exception as exc:
            failed_dates.append(
                {
                    "trade_date": trade_date,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:300],
                }
            )

        if index % 20 == 0 or index == len(open_dates):
            print(
                f"  progress {index}/{len(open_dates)} "
                f"fetched={fetched} reused={reused} failed={len(failed_dates)}"
            )

    print("[4/4] writing manifest")
    daily_files = sorted(DAILY_DIR.glob("*.json"))

    manifest = {
        "project": "Project Aegis",
        "type": "p23_2_historical_market_cache_manifest",
        "generated_at": now(),
        "start_date": START_DATE,
        "end_date": END_DATE,
        "trade_calendar": {
            "path": str(CALENDAR_PATH.relative_to(REPO)),
            "sha256": sha256_file(CALENDAR_PATH),
            "open_day_count": len(open_dates),
        },
        "stock_basic": {
            "path": str(STOCK_BASIC_PATH.relative_to(REPO)),
            "sha256": sha256_file(STOCK_BASIC_PATH),
            "row_count": int(len(stocks)),
        },
        "daily_cache": {
            "directory": str(DAILY_DIR.relative_to(REPO)),
            "expected_count": len(open_dates),
            "actual_count": len(daily_files),
            "fetched_this_run": fetched,
            "reused_this_run": reused,
            "failed_dates": failed_dates,
        },
        "dry_run": True,
        "sent": False,
        "trading_called": False,
    }

    complete = (
        not failed_dates
        and len(daily_files) == len(open_dates)
        and len(stocks) > 100
    )

    manifest["overall_verdict"] = "PASS" if complete else "FAIL"
    write_json(MANIFEST_PATH, manifest)

    print("P23_2_HISTORICAL_MARKET_CACHE_MANIFEST_JSON")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("END_P23_2_HISTORICAL_MARKET_CACHE_MANIFEST_JSON")

    return 0 if complete else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"[build_p23_2_historical_market_cache] "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)

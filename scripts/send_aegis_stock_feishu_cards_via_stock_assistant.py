#!/usr/bin/env python3
"""Send Aegis Feishu presentations through the OpenClaw stock account.

This wrapper intentionally uses ``openclaw message send --account stock``.
Do not import stock-picker/push.py here: its local .env may point at the
AI-news Feishu app, which would make messages appear from the wrong assistant.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "data" / "reports"
CARDS = REPORTS / "aegis_stock_assistant_feishu_cards_latest.json"
PRESENTATIONS = REPORTS / "aegis_stock_assistant_feishu_presentations_latest.json"
OUTPUT = REPORTS / "aegis_stock_assistant_feishu_send_latest.json"
OPENCLAW_HOME = Path.home() / ".openclaw"
STOCK_ALLOW_FROM = OPENCLAW_HOME / "credentials" / "feishu-stock-allowFrom.json"
OPENCLAW_CONFIG = OPENCLAW_HOME / "openclaw.json"
OPENCLAW_SECRETREFS = OPENCLAW_HOME / "secrets" / "openclaw-secretrefs.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _arg_value(argv: list[str], name: str) -> str:
    if name not in argv:
        return ""
    idx = argv.index(name)
    if idx + 1 >= len(argv):
        return ""
    return argv[idx + 1].strip()


def _target(argv: list[str]) -> str:
    return (
        _arg_value(argv, "--target")
        or os.environ.get("AEGIS_FEISHU_TARGET", "").strip()
        or _stock_allow_target()
    )


def _stock_allow_target() -> str:
    if not STOCK_ALLOW_FROM.exists():
        return ""
    try:
        allow_from = json.loads(STOCK_ALLOW_FROM.read_text(encoding="utf-8")).get("allowFrom") or []
    except (OSError, json.JSONDecodeError):
        return ""
    return str(allow_from[0]).strip() if allow_from else ""


def _fallback_text(presentation: dict[str, Any]) -> str:
    blocks = presentation.get("blocks") or []
    texts = [presentation.get("title") or "Aegis 股票候选"]
    for block in blocks:
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
    return "\n\n".join(t for t in texts if t).strip()


def _send_error_summary(output: str) -> str:
    if "ERR_FR_TOO_MANY_REDIRECTS" in output:
        return "openclaw_feishu_token_redirect_loop"
    if "open_id cross app" in output:
        return "feishu_open_id_cross_app"
    return "openclaw_message_send_failed"


def send_presentations(presentations: list[dict[str, Any]], target: str, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "send_status": "DRY_RUN",
            "sent_count": 0,
            "failed_count": 0,
            "results": [],
            "reason": "missing target or --dry-run",
        }

    results: list[dict[str, Any]] = []
    sent_count = 0
    failed_count = 0
    for index, presentation in enumerate(presentations, 1):
        cmd = [
            "openclaw",
            "message",
            "send",
            "--channel",
            "feishu",
            "--account",
            "stock",
            "--target",
            target,
            "--message",
            _fallback_text(presentation),
            "--presentation",
            json.dumps(presentation, ensure_ascii=False),
            "--json",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        ok = result.returncode == 0
        sent_count += 1 if ok else 0
        failed_count += 0 if ok else 1
        results.append(
            {
                "index": index,
                "sent": ok,
                "account": "stock",
                "reason": None if ok else _send_error_summary((result.stderr or result.stdout).strip()),
            }
        )
    return {
        "send_status": "SENT" if sent_count and not failed_count else "PARTIAL_OR_FAILED",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "transport": "openclaw_message_send",
        "results": results,
    }


def _post_json(url: str, payload: dict[str, Any], token: str | None = None) -> tuple[int, dict[str, Any]]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", "replace")
        return response.status, json.loads(body)


def _stock_tenant_token() -> str:
    config = json.loads(OPENCLAW_CONFIG.read_text(encoding="utf-8"))
    secretrefs = json.loads(OPENCLAW_SECRETREFS.read_text(encoding="utf-8"))
    account = config["channels"]["feishu"]["accounts"]["stock"]
    app_secret = secretrefs["openclaw_json"]["channels"]["feishu"]["accounts"]["stock"]["appSecret"]
    _, payload = _post_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        {"app_id": account["appId"], "app_secret": app_secret},
    )
    if payload.get("code") != 0 or not payload.get("tenant_access_token"):
        raise RuntimeError(f"stock token failed: code={payload.get('code')} msg={payload.get('msg')}")
    return payload["tenant_access_token"]


def send_cards_direct(cards: list[dict[str, Any]], target: str, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "send_status": "DRY_RUN",
            "sent_count": 0,
            "failed_count": 0,
            "transport": "feishu_official_api_stock_app",
            "results": [],
            "reason": "missing target or --dry-run",
        }

    token = _stock_tenant_token()
    results: list[dict[str, Any]] = []
    sent_count = 0
    failed_count = 0
    for index, card in enumerate(cards, 1):
        try:
            status, payload = _post_json(
                "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
                {
                    "receive_id": target,
                    "msg_type": "interactive",
                    "content": json.dumps(card, ensure_ascii=False),
                },
                token=token,
            )
            ok = status == 200 and payload.get("code") == 0
            sent_count += 1 if ok else 0
            failed_count += 0 if ok else 1
            results.append(
                {
                    "index": index,
                    "sent": ok,
                    "account": "stock",
                    "http_status": status,
                    "feishu_code": payload.get("code"),
                    "message_id": (payload.get("data") or {}).get("message_id"),
                    "reason": None if ok else payload.get("msg"),
                }
            )
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            failed_count += 1
            results.append(
                {
                    "index": index,
                    "sent": False,
                    "account": "stock",
                    "reason": f"{type(exc).__name__}: {str(exc)[:200]}",
                }
            )
    return {
        "send_status": "SENT" if sent_count and not failed_count else "PARTIAL_OR_FAILED",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "transport": "feishu_official_api_stock_app",
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    forced_dry_run = "--dry-run" in argv
    target = _target(argv)
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    presentations = json.loads(PRESENTATIONS.read_text(encoding="utf-8"))
    dry_run = forced_dry_run or not target
    result = send_presentations(presentations, target=target, dry_run=dry_run)
    if (
        result["send_status"] == "PARTIAL_OR_FAILED"
        and result["sent_count"] == 0
        and "--no-direct-fallback" not in argv
    ):
        result["openclaw_attempt"] = result["results"]
        result.update(send_cards_direct(cards, target=target, dry_run=dry_run))
    report = {
        "type": "aegis_stock_assistant_feishu_send",
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(),
        "sender": "openclaw_stock_account",
        "channel": "feishu",
        "account": "stock",
        "target_present": bool(target),
        "cards_path": str(CARDS),
        "cards_sha256": _sha256(CARDS),
        "presentations_path": str(PRESENTATIONS),
        "presentations_sha256": _sha256(PRESENTATIONS),
        "card_count": len(cards),
        "presentation_count": len(presentations),
        **result,
        "safety": {
            "simulation_only": True,
            "no_broker_api": True,
            "no_order_placement": True,
            "no_trading_webhook": True,
            "no_secret_values_recorded": True,
        },
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"output={OUTPUT}")
    print(f"status={report['send_status']}")
    print(f"sent_count={report['sent_count']}")
    print(f"failed_count={report['failed_count']}")
    return 0 if report["send_status"] in {"SENT", "DRY_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

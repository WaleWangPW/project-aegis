#!/usr/bin/env python3
"""serve_desktop.py — P1C optional local server.

Serves **only** the `data/desktop/` directory (the read-only status page
built by `scripts/build_desktop_status.py`) over plain HTTP, bound only
to `127.0.0.1` — never `0.0.0.0`, never any other interface. No auth
(P1C scope explicitly allows "no auth complexity ... unless already
present and tested" — none exists yet, so none is added here). This is
a convenience viewer only; it serves static files and nothing else — no
API routes, no write operations, no code execution.

If port 8765 is already in use:
    lsof -i :8765          # find the process holding it
    kill <pid>              # stop it
or simply pick another port:
    python scripts/serve_desktop.py --port 8766

Usage:
    python scripts/serve_desktop.py
    python scripts/serve_desktop.py --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import argparse
import functools
import http.server
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERVE_DIR = REPO_ROOT / "data" / "desktop"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class _RestrictedHandler(http.server.SimpleHTTPRequestHandler):
    """Plain static file handler with directory listing disabled and the
    served root fixed at construction time via `functools.partial` —
    never derived from the request itself."""

    def list_directory(self, path):  # noqa: D102 - stdlib override
        self.send_error(403, "Directory listing is disabled")
        return None


def build_server(host: str, port: int, serve_dir: Path) -> http.server.HTTPServer:
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError(
            f"serve_desktop.py only binds to 127.0.0.1 (got {host!r}) — this is a local-only "
            "read-only viewer, never exposed to the network."
        )
    handler = functools.partial(_RestrictedHandler, directory=str(serve_dir))
    return http.server.HTTPServer((host, port), handler)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve data/desktop/ (the read-only Aegis status page) on 127.0.0.1 only."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Must be 127.0.0.1 (or localhost) — enforced.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--serve-dir", default=str(DEFAULT_SERVE_DIR))
    args = parser.parse_args(argv)

    serve_dir = Path(args.serve_dir)
    serve_dir.mkdir(parents=True, exist_ok=True)

    try:
        server = build_server(args.host, args.port, serve_dir)
    except ValueError as exc:
        print(f"serve_desktop.py argument error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(
            f"serve_desktop.py could not bind {args.host}:{args.port}: {exc}. "
            f"If the port is already in use, find the process with `lsof -i :{args.port}` and stop it, "
            "or pass --port to use a different one.",
            file=sys.stderr,
        )
        return 1

    print(f"Serving {serve_dir} at http://{args.host}:{args.port}/aegis_status.html (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

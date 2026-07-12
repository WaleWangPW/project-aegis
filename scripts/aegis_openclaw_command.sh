#!/usr/bin/env bash
# aegis_openclaw_command.sh — P1C.2 tiny OpenClaw/Feishu command wrapper.
#
# Runs scripts/openclaw_aegis_readonly.py with all arguments joined into
# one command string, e.g.:
#
#   ./scripts/aegis_openclaw_command.sh aegis status
#   ./scripts/aegis_openclaw_command.sh "aegis holdings"
#
# This wrapper adds no logic of its own: no allow/forbid decisions, no
# secrets, no write operations, no network calls. It exists only so an
# OpenClaw/Feishu integration can invoke one short, stable shell command
# instead of a full `python scripts/openclaw_aegis_readonly.py "..."`
# invocation. Every permission decision still happens entirely inside
# scripts/aegis_agent_gateway.py.
#
# Exit code and stdout are passed straight through from the adapter.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

exec python3 "${REPO_ROOT}/scripts/openclaw_aegis_readonly.py" "$*"

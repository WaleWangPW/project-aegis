"""Load user-provided external API connector metadata."""

from __future__ import annotations

import json
from pathlib import Path

from aegis.models.external_api import ExternalAPIConnectorSpec


class APIConfigError(ValueError):
    pass


def load_api_connector_specs(path: Path) -> list[ExternalAPIConnectorSpec]:
    if not path.exists():
        raise APIConfigError(f"API connector config not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    specs = [ExternalAPIConnectorSpec(**item) for item in payload.get("connectors", [])]
    if not specs:
        raise APIConfigError("API connector config contains no connectors")
    return specs


def get_api_connector_spec(path: Path, connector_id: str) -> ExternalAPIConnectorSpec:
    for spec in load_api_connector_specs(path):
        if spec.connector_id == connector_id:
            return spec
    raise APIConfigError(f"connector_id not found: {connector_id}")

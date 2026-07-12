"""External source registry and policy gate for Project Aegis."""

from aegis.external_sources.policy import evaluate_source_policy, evaluate_source_registry
from aegis.external_sources.fetcher import SourceFetchError, fetch_official_source_item

__all__ = [
    "SourceFetchError",
    "evaluate_source_policy",
    "evaluate_source_registry",
    "fetch_official_source_item",
]

"""Central logging configuration and helpers.

``configure_logging`` is called once at application startup so every logger
shares a consistent format and level; modules simply use
``logging.getLogger(__name__)``. ``to_loggable`` renders agent contracts (input
requests / output results) as a stable single-line JSON string for logging
without leaking raw receipt bytes (``docs/backend/security.md``).
"""
import json
import logging
from typing import Any

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging once (no-op if handlers are already present)."""
    logging.basicConfig(level=level, format=_LOG_FORMAT)


def to_loggable(value: Any) -> str:
    """Render a structured contract/object as single-line JSON for logging."""
    if value is None:
        return "null"
    if hasattr(value, "model_dump"):
        try:
            value = value.model_dump(mode="json")
        except Exception:
            value = str(value)
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)

"""In-memory ring buffer of recent webhook attempts for live setup debugging.

Enabled only when DIAGNOSTICS_ENABLED=1. Contents are lost on restart and
never persisted — this is a setup aid, not an audit log.
"""
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from api.config import settings

_buffer: deque[dict[str, Any]] = deque(maxlen=settings.diagnostics_buffer_size)
_lock = Lock()


def record(entry: dict[str, Any]) -> None:
    """Append a structured event. Safe to call even when diagnostics is disabled."""
    if not settings.diagnostics_enabled:
        return
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **entry}
    with _lock:
        _buffer.append(entry)


def snapshot(limit: int | None = None) -> list[dict[str, Any]]:
    """Return the most recent entries (newest last)."""
    with _lock:
        items = list(_buffer)
    if limit is not None:
        items = items[-limit:]
    return items


def clear() -> None:
    with _lock:
        _buffer.clear()

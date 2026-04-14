from cachetools import TTLCache

from api.config import settings

_event_cache: TTLCache = TTLCache(maxsize=10_000, ttl=settings.dedup_ttl_seconds)


def is_duplicate_event(student_id: str) -> bool:
    """Return True if this student was already processed within the TTL window."""
    if student_id in _event_cache:
        return True
    _event_cache[student_id] = True
    return False


def clear_cache() -> None:
    """Remove all entries from the cache (intended for testing)."""
    _event_cache.clear()

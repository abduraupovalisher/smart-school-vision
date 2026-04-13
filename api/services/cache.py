from cachetools import TTLCache

# Global TTL cache to prevent multiple event logs for the same student
# maxsize: number of items to store, ttl: time to live in seconds (30s)
_event_cache = TTLCache(maxsize=10000, ttl=30)


def is_duplicate_event(student_id: str) -> bool:
    """
    Checks if the student_id has already been processed recently.

    If student_id is in the cache:
        Return True (Duplicate)
    Else:
        Add it to the cache and return False (New)
    """
    if student_id in _event_cache:
        return True

    _event_cache[student_id] = True
    return False

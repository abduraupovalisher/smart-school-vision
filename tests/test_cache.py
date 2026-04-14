"""Unit tests for the in-memory event deduplication cache."""
from api.services.cache import clear_cache, is_duplicate_event


# conftest.py already runs clear_cache() before/after every test via autouse fixture


def test_first_event_not_duplicate():
    assert is_duplicate_event("student_1") is False


def test_second_call_is_duplicate():
    is_duplicate_event("student_1")
    assert is_duplicate_event("student_1") is True


def test_different_students_are_independent():
    is_duplicate_event("student_1")
    assert is_duplicate_event("student_2") is False


def test_clear_cache_resets_state():
    is_duplicate_event("student_1")
    clear_cache()
    assert is_duplicate_event("student_1") is False


def test_multiple_students():
    ids = [f"student_{i}" for i in range(5)]
    for sid in ids:
        assert is_duplicate_event(sid) is False  # First call: new
    for sid in ids:
        assert is_duplicate_event(sid) is True  # Second call: duplicate

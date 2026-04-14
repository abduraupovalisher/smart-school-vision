"""Unit tests for event_processor helpers (pure functions — no DB needed)."""
import os
import pytest

from api.exceptions import XMLParseError
from api.services.event_processor import _extract_student_id, _parse_xml, _save_snapshot

# ── XML samples ───────────────────────────────────────────────────────────────

XML_EMPLOYEE_NO = (
    "<?xml version='1.0'?>"
    "<EventNotificationAlert>"
    "  <employeeNoString>12345</employeeNoString>"
    "</EventNotificationAlert>"
)

XML_STUDENT_ID = (
    "<?xml version='1.0'?>"
    "<Root><Person><studentId>99</studentId></Person></Root>"
)

XML_NESTED = (
    "<?xml version='1.0'?>"
    "<Root><A><B><C><employeeNoString>777</employeeNoString></C></B></A></Root>"
)

XML_NO_ID = (
    "<?xml version='1.0'?>"
    "<EventNotificationAlert><eventType>faceRecognition</eventType></EventNotificationAlert>"
)

INVALID_XML = "this is <<< definitely not xml"


# ── _parse_xml ────────────────────────────────────────────────────────────────

def test_parse_valid_xml_string():
    result = _parse_xml(XML_EMPLOYEE_NO)
    assert isinstance(result, dict)
    assert "EventNotificationAlert" in result


def test_parse_valid_xml_bytes():
    result = _parse_xml(XML_EMPLOYEE_NO.encode())
    assert isinstance(result, dict)


def test_parse_invalid_xml_raises():
    with pytest.raises(XMLParseError):
        _parse_xml(INVALID_XML)


def test_parse_handles_utf8_with_errors():
    bad_bytes = b"<?xml version='1.0'?><Root>\xff\xfe</Root>"
    result = _parse_xml(bad_bytes)
    assert "Root" in result


# ── _extract_student_id ───────────────────────────────────────────────────────

def test_extract_employee_no():
    parsed = _parse_xml(XML_EMPLOYEE_NO)
    assert _extract_student_id(parsed) == "12345"


def test_extract_student_id_key():
    parsed = _parse_xml(XML_STUDENT_ID)
    assert _extract_student_id(parsed) == "99"


def test_extract_nested():
    parsed = _parse_xml(XML_NESTED)
    assert _extract_student_id(parsed) == "777"


def test_extract_returns_none_when_missing():
    parsed = _parse_xml(XML_NO_ID)
    assert _extract_student_id(parsed) is None


def test_extract_from_list():
    data = [{"employeeNoString": "55"}, {"other": "value"}]
    assert _extract_student_id(data) == "55"


def test_extract_from_plain_dict():
    assert _extract_student_id({"employeeNoString": "7"}) == "7"


# ── _save_snapshot ────────────────────────────────────────────────────────────

def test_save_snapshot_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr("api.services.event_processor.settings.snapshot_dir", str(tmp_path))
    path = _save_snapshot(b"\xff\xd8fake_jpeg")
    assert path is not None
    assert os.path.isfile(path)
    assert open(path, "rb").read() == b"\xff\xd8fake_jpeg"


def test_save_snapshot_returns_none_on_bad_dir(monkeypatch):
    monkeypatch.setattr(
        "api.services.event_processor.settings.snapshot_dir",
        "/nonexistent/path/that/cannot/be/created/because/root/owns/it",
    )
    # On most systems this will fail silently and return None
    monkeypatch.setattr("os.makedirs", lambda *a, **kw: (_ for _ in ()).throw(OSError("denied")))
    result = _save_snapshot(b"data")
    assert result is None

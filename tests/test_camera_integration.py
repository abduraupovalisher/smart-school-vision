"""
Integration tests using realistic Hikvision ISAPI payloads.

These tests replicate the exact XML schemas sent by Hikvision cameras with
built-in AI face recognition. The camera posts multipart/form-data to
POST /api/webhook with:
  - Part 1: XML (text/xml)  — event metadata including matched student ID
  - Part 2: JPEG (image/jpeg) — face snapshot captured by the camera AI

All tests run against an in-memory SQLite database — no physical camera needed.
"""
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func

from models import Camera, Event, Student

# ── Realistic Hikvision XML fixtures ─────────────────────────────────────────

def _xml_matched_face(employee_no: str, name: str = "Test Student", similarity: float = 96.0) -> bytes:
    """Full ISAPI faceRecognition XML for a successfully matched (known) face."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert version="2.0"
    xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <ipAddress>192.168.1.100</ipAddress>
    <portNo>80</portNo>
    <protocol>HTTP</protocol>
    <channelID>1</channelID>
    <dateTime>2026-04-14T08:30:00+05:00</dateTime>
    <activePostCount>1</activePostCount>
    <eventType>faceRecognition</eventType>
    <eventState>active</eventState>
    <eventDescription>Face Recognition Alarm</eventDescription>
    <faceRecognitionAlarmList>
        <faceRecognitionAlarm>
            <currImg>
                <picName>faceSnapShot</picName>
            </currImg>
            <faceLibType>blackFD</faceLibType>
            <FDID>1</FDID>
            <FUID>{employee_no}</FUID>
            <FDName>Student_List</FDName>
            <FDContrastStatus>matched</FDContrastStatus>
            <matchedFDInfo>
                <FDID>1</FDID>
                <FUID>{employee_no}</FUID>
                <employeeNoString>{employee_no}</employeeNoString>
                <name>{name}</name>
                <sex>male</sex>
                <similarity>{similarity}</similarity>
            </matchedFDInfo>
        </faceRecognitionAlarm>
    </faceRecognitionAlarmList>
</EventNotificationAlert>""".encode()


def _xml_unmatched_face() -> bytes:
    """ISAPI faceRecognition XML for an unrecognised (unknown) person."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert version="2.0"
    xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <ipAddress>192.168.1.100</ipAddress>
    <channelID>1</channelID>
    <dateTime>2026-04-14T08:31:00+05:00</dateTime>
    <eventType>faceRecognition</eventType>
    <eventState>active</eventState>
    <faceRecognitionAlarmList>
        <faceRecognitionAlarm>
            <faceLibType>blackFD</faceLibType>
            <FDContrastStatus>unmatched</FDContrastStatus>
        </faceRecognitionAlarm>
    </faceRecognitionAlarmList>
</EventNotificationAlert>"""


def _xml_older_firmware(employee_no: str) -> bytes:
    """Flatter XML schema used by some older Hikvision firmware versions."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert>
    <ipAddress>192.168.1.101</ipAddress>
    <channelID>1</channelID>
    <eventType>faceRecognition</eventType>
    <employeeNoString>{employee_no}</employeeNoString>
    <name>Legacy Student</name>
    <similarity>88.0</similarity>
</EventNotificationAlert>""".encode()


_DUMMY_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64  # Minimal valid JPEG header + padding


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def registered_camera(db_session) -> Camera:
    cam = Camera(ip_address="192.168.1.100", entrance_name="Main Entrance")
    db_session.add(cam)
    db_session.commit()
    return cam


@pytest.fixture
def known_student(db_session) -> Student:
    student = Student(full_name="Ali Karimov", class_name="10A")
    db_session.add(student)
    db_session.commit()
    return student


# ── HTTP response tests ───────────────────────────────────────────────────────

class TestWebhookResponse:
    """Webhook must always return 200 — regardless of payload content."""

    def test_matched_face_returns_200(self, client: TestClient, registered_camera):
        resp = client.post(
            "/api/webhook",
            files={
                "xml_file": ("event.xml", _xml_matched_face("12345"), "text/xml"),
                "image_file": ("snap.jpg", _DUMMY_JPEG, "image/jpeg"),
            },
        )
        assert resp.status_code == 200

    def test_unmatched_face_returns_200(self, client: TestClient, registered_camera):
        resp = client.post(
            "/api/webhook",
            files={
                "xml_file": ("event.xml", _xml_unmatched_face(), "text/xml"),
                "image_file": ("snap.jpg", _DUMMY_JPEG, "image/jpeg"),
            },
        )
        assert resp.status_code == 200

    def test_older_firmware_returns_200(self, client: TestClient):
        resp = client.post(
            "/api/webhook",
            files={"xml_file": ("event.xml", _xml_older_firmware("99"), "text/xml")},
        )
        assert resp.status_code == 200


# ── XML parsing tests ─────────────────────────────────────────────────────────

class TestHikvisionXMLParsing:
    """Verify that student IDs are extracted correctly from realistic payloads."""

    def test_extracts_employee_no_from_matched_face(self):
        from api.services.event_processor import _extract_student_id, _parse_xml
        parsed = _parse_xml(_xml_matched_face("42001"))
        assert _extract_student_id(parsed) == "42001"

    def test_returns_none_for_unmatched_face(self):
        from api.services.event_processor import _extract_student_id, _parse_xml
        parsed = _parse_xml(_xml_unmatched_face())
        assert _extract_student_id(parsed) is None

    def test_extracts_employee_no_from_older_firmware(self):
        from api.services.event_processor import _extract_student_id, _parse_xml
        parsed = _parse_xml(_xml_older_firmware("8801"))
        assert _extract_student_id(parsed) == "8801"

    def test_high_similarity_is_preserved(self):
        """Ensure the XML body with 99.9% similarity parses without errors."""
        from api.services.event_processor import _parse_xml
        result = _parse_xml(_xml_matched_face("1", similarity=99.9))
        assert result is not None


# ── Deduplication tests ───────────────────────────────────────────────────────

class TestDeduplication:
    """Camera AI can fire the same face multiple times in quick succession."""

    def test_second_event_within_ttl_is_skipped(self, client: TestClient, db_session, registered_camera):
        payload = {"xml_file": ("event.xml", _xml_matched_face("55555"), "text/xml")}
        client.post("/api/webhook", files=payload)
        client.post("/api/webhook", files=payload)

        count = db_session.query(func.count(Event.id)).filter(
            Event.camera_id == "Main Entrance"
        ).scalar()
        assert count == 1  # second event deduplicated

    def test_different_students_are_not_deduplicated(self, client: TestClient, db_session, registered_camera):
        client.post(
            "/api/webhook",
            files={"xml_file": ("event.xml", _xml_matched_face("AAA01"), "text/xml")},
        )
        client.post(
            "/api/webhook",
            files={"xml_file": ("event.xml", _xml_matched_face("BBB02"), "text/xml")},
        )

        count = db_session.query(func.count(Event.id)).filter(
            Event.camera_id == "Main Entrance"
        ).scalar()
        assert count == 2

    def test_unknown_faces_are_never_deduplicated(self, client: TestClient, db_session, registered_camera):
        """Unknown faces have no student ID so dedup cache never fires."""
        payload = {"xml_file": ("event.xml", _xml_unmatched_face(), "text/xml")}
        client.post("/api/webhook", files=payload)
        client.post("/api/webhook", files=payload)

        count = db_session.query(func.count(Event.id)).filter(
            Event.is_unknown.is_(True)
        ).scalar()
        assert count == 2


# ── Camera registration tests ─────────────────────────────────────────────────

class TestCameraRegistration:
    """Events from unregistered cameras should still be persisted."""

    def test_unregistered_camera_uses_unknown_entrance(self, client: TestClient, db_session):
        client.post(
            "/api/webhook",
            files={"xml_file": ("event.xml", _xml_matched_face("77777"), "text/xml")},
        )
        event = db_session.query(Event).filter(Event.camera_id == "Unknown Entrance").first()
        assert event is not None

    def test_registered_camera_uses_correct_entrance(self, client: TestClient, db_session, registered_camera):
        client.post(
            "/api/webhook",
            files={"xml_file": ("event.xml", _xml_matched_face("88888"), "text/xml")},
        )
        event = db_session.query(Event).filter(Event.camera_id == "Main Entrance").first()
        assert event is not None

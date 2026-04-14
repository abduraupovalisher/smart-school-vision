"""Integration tests for POST /api/webhook — the Hikvision ISAPI endpoint."""
import pytest
from fastapi.testclient import TestClient

VALID_XML = (
    b"<?xml version='1.0' encoding='UTF-8'?>"
    b"<EventNotificationAlert>"
    b"  <employeeNoString>42</employeeNoString>"
    b"  <eventType>faceRecognition</eventType>"
    b"</EventNotificationAlert>"
)
DUMMY_JPEG = b"\xff\xd8\xff\xe0" + b"fake_jpeg_payload"


def test_webhook_returns_200_for_xml_only(client: TestClient):
    resp = client.post(
        "/api/webhook",
        files={"xml_file": ("event.xml", VALID_XML, "text/xml")},
    )
    assert resp.status_code == 200


def test_webhook_returns_200_for_xml_and_image(client: TestClient):
    resp = client.post(
        "/api/webhook",
        files={
            "xml_file": ("event.xml", VALID_XML, "text/xml"),
            "image_file": ("snap.jpg", DUMMY_JPEG, "image/jpeg"),
        },
    )
    assert resp.status_code == 200


def test_webhook_returns_200_with_no_body(client: TestClient):
    """Camera must always get 200 even when the request is empty."""
    resp = client.post("/api/webhook")
    assert resp.status_code == 200


def test_webhook_returns_200_for_malformed_xml(client: TestClient):
    """Malformed XML must not crash the endpoint — still return 200."""
    resp = client.post(
        "/api/webhook",
        files={"xml_file": ("event.xml", b"not xml at all <<<", "text/xml")},
    )
    assert resp.status_code == 200


def test_webhook_detects_xml_by_magic_bytes(client: TestClient):
    """XML part should be detected by content prefix even without text/xml content-type."""
    resp = client.post(
        "/api/webhook",
        files={"xml_file": ("event.xml", VALID_XML, "application/octet-stream")},
    )
    assert resp.status_code == 200


def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

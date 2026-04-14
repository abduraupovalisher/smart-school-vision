"""Tests for the camera IP → entrance name mapping service."""
from api.services.mapping import get_entrance_by_ip
from models import Camera


def test_known_ip_returns_entrance_name(db_session, sample_camera: Camera):
    result = get_entrance_by_ip(sample_camera.ip_address, db_session)
    assert result == "Main Gate"


def test_unknown_ip_returns_fallback(db_session):
    result = get_entrance_by_ip("10.0.0.99", db_session)
    assert result == "Unknown Entrance"


def test_multiple_cameras(db_session):
    db_session.add(Camera(ip_address="10.1.1.1", entrance_name="East Wing"))
    db_session.add(Camera(ip_address="10.1.1.2", entrance_name="West Wing"))
    db_session.commit()

    assert get_entrance_by_ip("10.1.1.1", db_session) == "East Wing"
    assert get_entrance_by_ip("10.1.1.2", db_session) == "West Wing"
    assert get_entrance_by_ip("10.1.1.3", db_session) == "Unknown Entrance"

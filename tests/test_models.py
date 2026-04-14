"""Tests for SQLAlchemy models and database constraints."""
import pytest
from sqlalchemy.exc import IntegrityError

from models import Camera, Event, FaceEmbedding, Student, UnknownFace


# ── Student ───────────────────────────────────────────────────────────────────

def test_create_student(db_session):
    student = Student(full_name="Zara Mirzayeva", class_name="9B")
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    assert student.id is not None
    assert student.full_name == "Zara Mirzayeva"
    assert student.is_active is True  # default


def test_student_inactive(db_session):
    student = Student(full_name="Old Student", is_active=False)
    db_session.add(student)
    db_session.commit()
    assert student.is_active is False


# ── Camera ────────────────────────────────────────────────────────────────────

def test_create_camera(db_session):
    cam = Camera(ip_address="192.168.200.1", entrance_name="Side Gate")
    db_session.add(cam)
    db_session.commit()
    db_session.refresh(cam)

    assert cam.id is not None
    assert cam.is_active is True  # default


def test_camera_ip_must_be_unique(db_session):
    db_session.add(Camera(ip_address="192.168.250.1", entrance_name="Gate A"))
    db_session.commit()
    db_session.add(Camera(ip_address="192.168.250.1", entrance_name="Gate B"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ── Event ─────────────────────────────────────────────────────────────────────

def test_create_event_for_known_student(db_session, sample_student: Student):
    event = Event(
        student_id=sample_student.id,
        event_type="IN",
        camera_id="Main Gate",
        is_unknown=False,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.id is not None
    assert event.created_at is not None
    assert event.confidence == 0.0  # default


def test_create_event_for_unknown_face(db_session):
    event = Event(event_type="IN", camera_id="Main Gate", is_unknown=True)
    db_session.add(event)
    db_session.commit()

    assert event.student_id is None
    assert event.is_unknown is True


# ── FaceEmbedding ─────────────────────────────────────────────────────────────

def test_create_face_embedding(db_session, sample_student: Student):
    embedding = FaceEmbedding(student_id=sample_student.id, vector=b"\x00\x01\x02\x03")
    db_session.add(embedding)
    db_session.commit()
    db_session.refresh(embedding)

    assert embedding.id is not None
    assert embedding.created_at is not None


# ── UnknownFace ───────────────────────────────────────────────────────────────

def test_create_unknown_face(db_session):
    face = UnknownFace(vector=b"\xff\xfe\xfd", best_snapshot_path="data/snapshots/test.jpg")
    db_session.add(face)
    db_session.commit()
    db_session.refresh(face)

    assert face.id is not None
    assert face.status == "new"  # default
    assert face.seen_count == 1  # default

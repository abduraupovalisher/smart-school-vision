"""Shared pytest fixtures for the Smart School Vision test suite.

Isolation model:
    A single in-memory SQLite engine is created per session, tables created
    once. For each test, a connection opens an outer transaction and the
    session is bound to it with a SAVEPOINT, so any `session.commit()` inside
    the test is rolled back on teardown. This keeps tests hermetic even when
    they commit data (which FastAPI routes do via their own SessionLocal).
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

import database as db_module
from database import Base, get_db
from api.main import app
from api.services.cache import clear_cache
from models import Camera, Student

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(db_engine):
    """One connection per test, wrapped in an outer transaction."""
    conn = db_engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()


@pytest.fixture
def db_session(db_connection):
    """Session bound to the test connection with a SAVEPOINT so commits roll back."""
    SessionLocal = sessionmaker(bind=db_connection)
    session = SessionLocal()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, transaction):
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session, monkeypatch):
    """TestClient with both get_db and SessionLocal pointed at the test session.

    The webhook's background task calls `SessionLocal()` directly (not via
    FastAPI DI), so we monkeypatch it too — otherwise background writes would
    land in the real on-disk DB and be invisible to the test.
    """
    def _override_get_db():
        yield db_session

    def _session_factory():
        return _PassthroughSession(db_session)

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr(db_module, "SessionLocal", _session_factory)
    # event_processor imports SessionLocal at module import time:
    from api.services import event_processor as ep
    monkeypatch.setattr(ep, "SessionLocal", _session_factory)

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class _PassthroughSession:
    """Wrap the test session so `close()` is a no-op — the fixture owns its lifecycle."""
    def __init__(self, session: Session):
        self._s = session

    def __getattr__(self, name):
        return getattr(self._s, name)

    def close(self):
        pass


@pytest.fixture(autouse=True)
def reset_event_cache():
    """Clear the in-memory dedup cache before and after every test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def sample_camera(db_session) -> Camera:
    cam = Camera(ip_address="192.168.1.100", entrance_name="Main Gate")
    db_session.add(cam)
    db_session.commit()
    db_session.refresh(cam)
    return cam


@pytest.fixture
def sample_student(db_session) -> Student:
    student = Student(full_name="Ali Karimov", class_name="10A")
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student

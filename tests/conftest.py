"""Shared pytest fixtures for the Smart School Vision test suite."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

import database as db_module
from database import Base, get_db
from api.main import app
from api.services.cache import clear_cache
from models import Camera, Student

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provide a transactional DB session that rolls back after each test."""
    TestingSession = sessionmaker(bind=db_engine)
    session = TestingSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with DB dependency overridden to use the test session."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


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

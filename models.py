from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.dialects.sqlite import BLOB
from datetime import datetime
from database import Base

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    class_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    vector = Column(BLOB, nullable=False)  # embedding bytes
    created_at = Column(DateTime, default=datetime.utcnow)

class UnknownFace(Base):
    __tablename__ = "unknown_faces"
    id = Column(Integer, primary_key=True, index=True)
    vector = Column(BLOB, nullable=False)
    best_snapshot_path = Column(String, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    seen_count = Column(Integer, default=1)
    status = Column(String, default="new")  # new/reviewed/linked/ignored
    linked_student_id = Column(Integer, ForeignKey("students.id"), nullable=True)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    unknown_id = Column(Integer, ForeignKey("unknown_faces.id"), nullable=True)

    event_type = Column(String, nullable=False)  # IN / OUT
    camera_id = Column(String, nullable=True)
    confidence = Column(Float, default=0.0)
    snapshot_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    is_unknown = Column(Boolean, default=False)

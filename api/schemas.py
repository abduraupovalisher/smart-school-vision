from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class EventResponse(BaseModel):
    id: int
    student_id: Optional[int]
    event_type: str
    camera_id: Optional[str]
    snapshot_path: Optional[str]
    created_at: datetime
    is_unknown: bool

    model_config = {"from_attributes": True}


class CameraCreate(BaseModel):
    ip_address: str
    entrance_name: str
    is_active: bool = True


class StudentCreate(BaseModel):
    full_name: str
    class_name: Optional[str] = None
    is_active: bool = True

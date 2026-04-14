import logging
import os
import uuid

import xmltodict

from api.config import settings
from api.exceptions import XMLParseError
from api.services.cache import is_duplicate_event
from api.services.mapping import get_entrance_by_ip
from database import SessionLocal
from models import Event

logger = logging.getLogger(__name__)


def _parse_xml(xml_data: bytes | str) -> dict:
    """Parse raw XML into a dict. Raises XMLParseError on failure."""
    if isinstance(xml_data, bytes):
        xml_data = xml_data.decode("utf-8", errors="ignore")
    try:
        return xmltodict.parse(xml_data)
    except Exception as exc:
        raise XMLParseError(f"Failed to parse XML: {exc}") from exc


def _extract_student_id(data: object) -> str | None:
    """Recursively search parsed XML for Hikvision employee/student ID fields."""
    if isinstance(data, dict):
        for key, value in data.items():
            if "employeeNo" in key or "studentId" in key:
                return str(value)
            found = _extract_student_id(value)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _extract_student_id(item)
            if found:
                return found
    return None


def _save_snapshot(image_data: bytes) -> str | None:
    """Write a JPEG snapshot to disk and return the file path, or None on failure."""
    try:
        os.makedirs(settings.snapshot_dir, exist_ok=True)
        path = os.path.join(settings.snapshot_dir, f"snap_{uuid.uuid4().hex}.jpg")
        with open(path, "wb") as fh:
            fh.write(image_data)
        return path
    except OSError as exc:
        logger.error("Could not save snapshot: %s", exc)
        return None


def process_isapi_event(
    client_ip: str,
    xml_data: bytes | str,
    image_data: bytes | None,
    request_id: str = "",
) -> None:
    """Background task: parse the ISAPI event, deduplicate, persist snapshot + DB record."""
    tag = f"[{request_id}] " if request_id else ""

    try:
        parsed = _parse_xml(xml_data)
    except XMLParseError as exc:
        logger.error("%s%s", tag, exc)
        return

    student_id = _extract_student_id(parsed) or "unknown"

    if student_id != "unknown" and is_duplicate_event(student_id):
        logger.info("%sDuplicate event for student %s — skipped", tag, student_id)
        return

    snapshot_path = _save_snapshot(image_data) if image_data else None

    db = SessionLocal()
    try:
        entrance = get_entrance_by_ip(client_ip, db)
        db_student_id = int(student_id) if student_id.isdigit() else None

        event = Event(
            student_id=db_student_id,
            event_type="IN",
            camera_id=entrance,
            snapshot_path=snapshot_path,
            is_unknown=(student_id == "unknown"),
        )
        db.add(event)
        db.commit()
        logger.info("%sSaved event student=%s entrance=%s", tag, student_id, entrance)
    except Exception:
        db.rollback()
        logger.exception("%sDatabase error while saving event", tag)
    finally:
        db.close()

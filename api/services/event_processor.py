import os
import uuid
import logging
import xmltodict
from database import SessionLocal
from models import Event, Student
from api.services.mapping import get_entrance_by_ip
from api.services.cache import is_duplicate_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_isapi_event(
    client_ip: str, xml_data: bytes | str, image_data: bytes | None
):
    """
    Background task to process the ISAPI event:
    1. Parse XML to extract Student ID
    2. Map Camera IP to Entrance Name
    3. Check for duplicates (de-duplication)
    4. Save snapshot to disk
    5. Record event in the database
    """
    try:
        # Decode XML if necessary
        if isinstance(xml_data, bytes):
            xml_data = xml_data.decode("utf-8", errors="ignore")

        try:
            # Convert XML to dictionary for easier access
            parsed_xml = xmltodict.parse(xml_data)
        except Exception as e:
            logger.error(f"Failed to parse XML: {e}")
            return

        # Initialize student ID as unknown
        student_id = "unknown"

        def find_student_id(data):
            """Recursive helper to find student/employee ID in the nested XML structure"""
            if isinstance(data, dict):
                for k, v in data.items():
                    # Hikvision uses keys like employeeNoString or studentId
                    if "employeeNo" in k or "studentId" in k:
                        return str(v)
                    res = find_student_id(v)
                    if res:
                        return res
            elif isinstance(data, list):
                for item in data:
                    res = find_student_id(item)
                    if res:
                        return res
            return None

        found_id = find_student_id(parsed_xml)
        if found_id:
            student_id = found_id

        # Determine which gate this came from
        entrance_name = get_entrance_by_ip(client_ip)

        # De-duplication: Ignore if the same student was seen in the last 30 seconds
        if student_id != "unknown":
            if is_duplicate_event(student_id):
                logger.info(f"Duplicate event for student {student_id}, ignoring.")
                return

        # Save snapshot image if provided
        snapshot_path = None
        if image_data:
            os.makedirs("data/snapshots", exist_ok=True)
            filename = f"snap_{uuid.uuid4().hex}.jpg"
            snapshot_path = os.path.join("data/snapshots", filename)
            with open(snapshot_path, "wb") as f:
                f.write(image_data)

        # Persistence: Save the event to the database
        db = SessionLocal()
        try:
            db_student_id = None
            if student_id != "unknown" and student_id.isdigit():
                db_student_id = int(student_id)

            new_event = Event(
                student_id=db_student_id,
                event_type="IN",  # Defaulting to IN for entry tracking
                camera_id=entrance_name,
                snapshot_path=snapshot_path,
                is_unknown=(student_id == "unknown"),
            )
            db.add(new_event)
            db.commit()
            logger.info(f"Saved event for student {student_id} from {entrance_name}")
        except Exception as db_err:
            db.rollback()
            logger.error(f"Database error while saving event: {db_err}")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error processing ISAPI event: {e}", exc_info=True)

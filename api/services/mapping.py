from database import SessionLocal
from models import Camera


def get_entrance_by_ip(ip_address: str) -> str:
    """
    Looks up the human-readable entrance name (e.g., 'Main Gate')
    based on the camera's IP address by querying the 'cameras' table.
    """
    db = SessionLocal()
    try:
        # Query the Camera table for the IP address
        camera = db.query(Camera).filter(Camera.ip_address == ip_address).first()
        if camera:
            return camera.entrance_name
        return "Unknown Entrance"
    finally:
        # Always close the session to prevent leaks
        db.close()

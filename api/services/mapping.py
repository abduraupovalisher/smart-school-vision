import logging

from sqlalchemy.orm import Session

from models import Camera

logger = logging.getLogger(__name__)


def get_entrance_by_ip(ip_address: str, db: Session) -> str:
    """Return the human-readable entrance name for a camera IP address.

    Falls back to 'Unknown Entrance' when the IP is not registered.
    The caller is responsible for providing and closing the session.
    """
    camera = db.query(Camera).filter(Camera.ip_address == ip_address).first()
    if camera:
        return camera.entrance_name
    logger.debug("No camera registered for IP %s", ip_address)
    return "Unknown Entrance"

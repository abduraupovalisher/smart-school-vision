import uuid
import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response, UploadFile

from api.services.event_processor import process_isapi_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ISAPI"])

_XML_MAGIC = b"<?xml"
_JPEG_MAGIC = b"\xff\xd8"


@router.post("/webhook")
async def isapi_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    """
    Receive Hikvision ISAPI face-recognition events.

    The camera sends multipart/form-data with:
    - An XML part describing the event (student ID, event type)
    - An optional JPEG snapshot of the detected face

    Returns 200 immediately; all processing runs in a background task to
    prevent camera timeout.
    """
    request_id = uuid.uuid4().hex[:8]
    client_ip = request.client.host if request.client else "unknown"
    xml_data: bytes | None = None
    image_data: bytes | None = None

    try:
        form = await request.form()
        for _field, part in form.multi_items():
            if isinstance(part, UploadFile):
                content = await part.read()
                ct = part.content_type or ""
                if "xml" in ct or content.startswith(_XML_MAGIC):
                    xml_data = content
                elif "image" in ct or content.startswith(_JPEG_MAGIC):
                    image_data = content
            elif isinstance(part, str) and part.startswith("<?xml"):
                xml_data = part.encode()
    except Exception:
        logger.exception("[%s] Failed to parse multipart form from %s", request_id, client_ip)

    if xml_data:
        background_tasks.add_task(
            process_isapi_event, client_ip, xml_data, image_data, request_id
        )
    else:
        logger.warning("[%s] No XML in request from %s", request_id, client_ip)

    return Response(status_code=200)

import uuid
import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response, UploadFile

from api.services import diagnostics
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
    part_summary: list[str] = []

    try:
        form = await request.form()
        for _field, part in form.multi_items():
            if isinstance(part, UploadFile):
                content = await part.read()
                ct = part.content_type or ""
                part_summary.append(f"upload({ct or '?'},{len(content)}B)")
                if "xml" in ct or content.startswith(_XML_MAGIC):
                    xml_data = content
                elif "image" in ct or content.startswith(_JPEG_MAGIC):
                    image_data = content
            elif isinstance(part, str):
                part_summary.append(f"str({len(part)}B)")
                if part.startswith("<?xml"):
                    xml_data = part.encode()
    except Exception:
        logger.exception("[%s] Failed to parse multipart form from %s", request_id, client_ip)
        diagnostics.record({
            "request_id": request_id,
            "client_ip": client_ip,
            "stage": "multipart_parse",
            "ok": False,
            "error": "exception during form parse",
        })
        return Response(status_code=200)

    if xml_data:
        diagnostics.record({
            "request_id": request_id,
            "client_ip": client_ip,
            "stage": "webhook_received",
            "ok": True,
            "parts": part_summary,
            "xml_bytes": len(xml_data),
            "image_bytes": len(image_data) if image_data else 0,
        })
        background_tasks.add_task(
            process_isapi_event, client_ip, xml_data, image_data, request_id
        )
    else:
        logger.warning("[%s] No XML in request from %s (parts=%s)", request_id, client_ip, part_summary)
        diagnostics.record({
            "request_id": request_id,
            "client_ip": client_ip,
            "stage": "webhook_received",
            "ok": False,
            "parts": part_summary,
            "error": "no XML part found",
        })

    return Response(status_code=200)

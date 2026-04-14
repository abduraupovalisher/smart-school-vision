from fastapi import APIRouter, Request, BackgroundTasks, Response, UploadFile
from api.services.event_processor import process_isapi_event
import logging

logger = logging.getLogger(__name__)

# Router for Hikvision ISAPI events
router = APIRouter()


@router.post("/webhook")
async def isapi_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Main webhook to receive Hikvision event alerts.
    The camera sends multipart/form-data containing:
    1. XML data with event details (student ID, event type)
    2. JPEG image snapshot of the face
    """
    client_ip = request.client.host if request.client else "unknown"
    xml_data = None
    image_data = None

    try:
        # Parse multipart form data
        form = await request.form()
        for field_name, form_data in form.multi_items():
            if isinstance(form_data, UploadFile):
                content_type = form_data.content_type or ""
                content = await form_data.read()

                # Detect XML part
                if "xml" in content_type or content.startswith(b"<?xml"):
                    xml_data = content
                # Detect Image part
                elif "image" in content_type:
                    image_data = content
            elif isinstance(form_data, str):
                # Fallback for plain string XML
                if form_data.startswith("<?xml"):
                    xml_data = form_data.encode("utf-8")
    except Exception as e:
        logger.error(f"Error parsing ISAPI form data: {e}")

    # If we got the event XML, process it in the background to respond to the camera immediately
    if xml_data:
        background_tasks.add_task(process_isapi_event, client_ip, xml_data, image_data)

    # Return 200 OK as fast as possible to prevent camera timeout
    return Response(status_code=200)

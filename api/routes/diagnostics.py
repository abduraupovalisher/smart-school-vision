"""Read-only diagnostics endpoints, gated by DIAGNOSTICS_ENABLED."""
from fastapi import APIRouter, HTTPException, Query

from api.config import settings
from api.services import diagnostics

router = APIRouter(tags=["Diagnostics"], prefix="/diagnostics")


def _require_enabled() -> None:
    if not settings.diagnostics_enabled:
        raise HTTPException(
            status_code=404,
            detail="Diagnostics disabled. Set DIAGNOSTICS_ENABLED=1 to enable.",
        )


@router.get("/recent")
def recent(limit: int = Query(50, ge=1, le=500)) -> dict:
    """Return the most recent webhook attempts (newest last)."""
    _require_enabled()
    events = diagnostics.snapshot(limit=limit)
    return {
        "count": len(events),
        "buffer_size": settings.diagnostics_buffer_size,
        "events": events,
    }


@router.post("/clear")
def clear() -> dict:
    _require_enabled()
    diagnostics.clear()
    return {"status": "ok"}

"""Live camera integration tests — opt-in, skipped by default.

Purpose
-------
These are the tests you run *after* physically wiring a Hikvision camera to
the running API server and configuring it to POST to /api/webhook. They
verify the end-to-end path that unit tests cannot: the camera actually sends
events, your server's IP/port are reachable, the camera's IP is registered,
snapshots land on disk, and dedup behaves.

Running
-------
    # 1. Start the server with diagnostics enabled:
    DIAGNOSTICS_ENABLED=1 uvicorn api.main:app --host 0.0.0.0 --port 8000

    # 2. Configure the camera (see SETUP.md section 7).

    # 3. Register the camera in the DB:
    python -m scripts.register_camera add <camera-ip> "Main Entrance"

    # 4. In another terminal, run these tests and trigger faces on cue:
    pytest -m live -s
    # or point at a non-default server:
    LIVE_SERVER=http://192.168.1.50:8000 pytest -m live -s

Each test will PROMPT you to trigger a face in front of the camera, then
poll the diagnostics endpoint for the expected outcome. Run with `-s` so
prompts are visible.
"""
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

SERVER = os.getenv("LIVE_SERVER", "http://localhost:8000")
POLL_TIMEOUT = float(os.getenv("LIVE_POLL_TIMEOUT", "30"))
POLL_INTERVAL = 0.5

pytestmark = pytest.mark.live


# ── helpers ──────────────────────────────────────────────────────────────────

def _get(path: str, **kwargs) -> httpx.Response:
    return httpx.get(f"{SERVER}{path}", timeout=5.0, **kwargs)


def _recent(limit: int = 50) -> list[dict[str, Any]]:
    r = _get("/api/diagnostics/recent", params={"limit": limit})
    if r.status_code == 404:
        pytest.skip("Diagnostics disabled on server. Start it with DIAGNOSTICS_ENABLED=1.")
    r.raise_for_status()
    return r.json()["events"]


def _clear_diagnostics() -> None:
    httpx.post(f"{SERVER}/api/diagnostics/clear", timeout=5.0)


def _prompt(msg: str) -> None:
    print(f"\n>>> ACTION REQUIRED: {msg}")
    print(f">>> (waiting up to {POLL_TIMEOUT:.0f}s for the event to arrive)")


def _wait_for(predicate, timeout: float = POLL_TIMEOUT) -> list[dict[str, Any]] | None:
    """Poll /diagnostics/recent until predicate(events) returns truthy, or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        events = _recent()
        if predicate(events):
            return events
        time.sleep(POLL_INTERVAL)
    return None


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _server_up():
    try:
        r = httpx.get(f"{SERVER}/health", timeout=3.0)
        r.raise_for_status()
    except Exception as exc:
        pytest.skip(f"API server at {SERVER} not reachable: {exc}")


@pytest.fixture(autouse=True)
def _clean_slate():
    _clear_diagnostics()
    yield


# ── tests ────────────────────────────────────────────────────────────────────

def test_camera_delivers_any_webhook():
    """Camera can reach the server and POSTs a multipart webhook."""
    _prompt("Trigger ONE face in front of the camera (known or unknown).")
    events = _wait_for(lambda es: any(e["stage"] == "webhook_received" for e in es))
    assert events, "no webhook arrived within timeout — check camera network config and listener IP/port"
    arrivals = [e for e in events if e["stage"] == "webhook_received"]
    print(f">>> received {len(arrivals)} webhook(s); first parts={arrivals[0].get('parts')}")
    assert arrivals[0]["ok"], f"webhook arrived but had no XML part: {arrivals[0]}"


def test_known_face_persists_event_with_correct_entrance():
    """A matched face produces a persisted Event mapped to the registered entrance."""
    _prompt("Trigger a KNOWN student's face once.")
    events = _wait_for(lambda es: any(
        e["stage"] == "persisted" and e["ok"] and not e.get("is_unknown") for e in es
    ))
    assert events, "no matched-face event persisted — check /api/diagnostics/recent for details"
    persisted = [e for e in events if e["stage"] == "persisted" and e["ok"]][-1]
    print(f">>> student={persisted.get('student_id')} entrance={persisted.get('entrance')}")
    assert persisted["entrance"] != "Unknown Entrance", (
        f"camera IP {persisted['client_ip']} is not registered — "
        f"run: python -m scripts.register_camera add {persisted['client_ip']} <name>"
    )
    assert persisted.get("snapshot_path"), "no snapshot written — check SNAPSHOT_DIR permissions"


def test_dedup_suppresses_rapid_repeat():
    """Two rapid reads of the same face within the TTL produce exactly one persisted event."""
    _prompt("Hold the SAME known face in front of the camera for 5+ seconds so it fires twice.")
    events = _wait_for(lambda es: sum(
        1 for e in es if e["stage"] in ("persisted", "dedup")
    ) >= 2, timeout=POLL_TIMEOUT)
    assert events, "not enough events received to verify dedup"
    persisted = [e for e in events if e["stage"] == "persisted" and e["ok"]]
    deduped = [e for e in events if e["stage"] == "dedup" and e.get("skipped")]
    print(f">>> persisted={len(persisted)} deduped={len(deduped)}")
    assert len(persisted) >= 1, "expected at least one persisted event"
    assert len(deduped) >= 1, (
        "expected at least one dedup skip — either the TTL elapsed between reads "
        "or the camera sent different student IDs"
    )


def test_unknown_face_persists_as_unknown():
    """An unmatched face produces an Event with is_unknown=True."""
    _prompt("Trigger a face that is NOT enrolled in the camera's face library.")
    events = _wait_for(lambda es: any(
        e["stage"] == "persisted" and e.get("is_unknown") for e in es
    ))
    assert events, "no unknown-face event persisted"
    unknown = [e for e in events if e.get("is_unknown")][-1]
    print(f">>> unknown face recorded at entrance={unknown.get('entrance')}")

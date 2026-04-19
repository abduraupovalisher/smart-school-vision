"""One-shot health check for a Smart School Vision deployment.

Verifies:
  - DB reachable + schema present
  - At least one camera registered
  - Snapshot dir writable
  - API /health responds
  - Last event timestamp (distinguishes "camera silent" from "never connected")

Usage:
    python -m scripts.doctor
    python -m scripts.doctor --server http://192.168.1.50:8000
"""
import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, inspect

from api.config import settings
from database import SessionLocal, engine
from models import Camera, Event


OK = "  [OK] "
WARN = "  [WARN] "
FAIL = "  [FAIL] "


def check_database() -> bool:
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
    except Exception as exc:
        print(f"{FAIL}database unreachable: {exc}")
        return False
    required = {"students", "events", "cameras"}
    missing = required - tables
    if missing:
        print(f"{FAIL}database reachable but missing tables: {sorted(missing)}")
        print("        run the API server once to create them (uvicorn api.main:app)")
        return False
    print(f"{OK}database reachable: {settings.database_url}")
    return True


def check_cameras() -> bool:
    with SessionLocal() as db:
        count = db.query(func.count(Camera.id)).scalar() or 0
    if count == 0:
        print(f"{WARN}no cameras registered — events will fall back to 'Unknown Entrance'")
        print("        register one: python -m scripts.register_camera add <ip> <name>")
        return False
    print(f"{OK}{count} camera(s) registered")
    return True


def check_snapshot_dir() -> bool:
    path = settings.snapshot_dir
    try:
        os.makedirs(path, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, prefix=".doctor_", suffix=".tmp", delete=True):
            pass
    except OSError as exc:
        print(f"{FAIL}snapshot dir {path!r} not writable: {exc}")
        return False
    print(f"{OK}snapshot dir writable: {path}")
    return True


def check_http(server: str) -> bool:
    try:
        r = httpx.get(f"{server}/health", timeout=3.0)
        r.raise_for_status()
    except Exception as exc:
        print(f"{FAIL}API server at {server} not responding: {exc}")
        print("        start it: uvicorn api.main:app --host 0.0.0.0 --port 8000")
        return False
    print(f"{OK}API server responding at {server}")
    return True


def check_recent_events() -> None:
    with SessionLocal() as db:
        last = db.query(func.max(Event.created_at)).scalar()
        total = db.query(func.count(Event.id)).scalar() or 0
    if last is None:
        print(f"{WARN}no events in database yet — camera has never delivered a webhook")
        print("        try: python camera_simulator.py --student-id 1")
        return
    age = datetime.utcnow() - last
    age_str = f"{int(age.total_seconds())}s ago" if age.total_seconds() < 3600 else f"{age}"
    print(f"{OK}last event: {last.isoformat()} ({age_str}); total={total}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Smart School Vision health check")
    ap.add_argument("--server", default="http://localhost:8000", help="API base URL")
    args = ap.parse_args()

    print(f"Smart School Vision doctor — {datetime.now(timezone.utc).isoformat()}")
    print()

    results = [
        check_database(),
        check_cameras(),
        check_snapshot_dir(),
        check_http(args.server),
    ]
    check_recent_events()  # informational; does not affect exit code

    print()
    failed = results.count(False)
    if failed == 0:
        print("all checks passed.")
        return 0
    print(f"{failed} check(s) failed — address the items above before pointing a camera at the server.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

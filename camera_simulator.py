"""
Hikvision Camera Simulator
===========================
Sends realistic ISAPI faceRecognition payloads to the Smart School Vision server.
Useful for manual testing and verifying the server handles real camera traffic.

Usage examples:

  # Send one event for student 12345 from camera 192.168.1.100
  python camera_simulator.py --student-id 12345

  # Send an unmatched (unknown) face event
  python camera_simulator.py --unknown

  # Simulate 5 events for student 12345, 1 second apart
  python camera_simulator.py --student-id 12345 --count 5 --interval 1

  # Rapid burst to test deduplication (all within the 30-second TTL)
  python camera_simulator.py --student-id 12345 --count 10 --interval 0

  # Simulate multiple students arriving at once
  python camera_simulator.py --multi-student --count 3

  # Point at a non-default server
  python camera_simulator.py --student-id 1 --server http://192.168.1.50:8000
"""

import argparse
import io
import sys
import time
from datetime import datetime, timezone

import requests

DEFAULT_SERVER = "http://localhost:8000"
DEFAULT_CAMERA_IP = "192.168.1.100"
WEBHOOK_PATH = "/api/webhook"

# Minimal 1×1 pixel JPEG (valid for cameras that don't attach full images)
_MINIMAL_JPEG = bytes([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
    0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
    0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
    0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
    0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
    0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
    0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
    0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
    0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
    0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
    0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
    0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
    0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xFB, 0x00,
    0xFF, 0xD9,
])


def _build_matched_xml(
    employee_no: str,
    name: str,
    camera_ip: str,
    similarity: float = 96.5,
) -> str:
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert version="2.0"
    xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <ipAddress>{camera_ip}</ipAddress>
    <portNo>80</portNo>
    <protocol>HTTP</protocol>
    <channelID>1</channelID>
    <dateTime>{now}</dateTime>
    <activePostCount>1</activePostCount>
    <eventType>faceRecognition</eventType>
    <eventState>active</eventState>
    <eventDescription>Face Recognition Alarm</eventDescription>
    <faceRecognitionAlarmList>
        <faceRecognitionAlarm>
            <currImg>
                <picName>faceSnapShot</picName>
            </currImg>
            <faceLibType>blackFD</faceLibType>
            <FDID>1</FDID>
            <FUID>{employee_no}</FUID>
            <FDName>Student_List</FDName>
            <FDContrastStatus>matched</FDContrastStatus>
            <matchedFDInfo>
                <FDID>1</FDID>
                <FUID>{employee_no}</FUID>
                <employeeNoString>{employee_no}</employeeNoString>
                <name>{name}</name>
                <sex>unknown</sex>
                <similarity>{similarity}</similarity>
            </matchedFDInfo>
        </faceRecognitionAlarm>
    </faceRecognitionAlarmList>
</EventNotificationAlert>"""


def _build_unmatched_xml(camera_ip: str) -> str:
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert version="2.0"
    xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <ipAddress>{camera_ip}</ipAddress>
    <channelID>1</channelID>
    <dateTime>{now}</dateTime>
    <eventType>faceRecognition</eventType>
    <eventState>active</eventState>
    <faceRecognitionAlarmList>
        <faceRecognitionAlarm>
            <faceLibType>blackFD</faceLibType>
            <FDContrastStatus>unmatched</FDContrastStatus>
        </faceRecognitionAlarm>
    </faceRecognitionAlarmList>
</EventNotificationAlert>"""


def _send_event(server: str, xml: str, include_image: bool = True) -> tuple[int, float]:
    url = server.rstrip("/") + WEBHOOK_PATH
    files: dict = {"xml_file": ("event.xml", xml.encode(), "text/xml")}
    if include_image:
        files["image_file"] = ("snapshot.jpg", io.BytesIO(_MINIMAL_JPEG), "image/jpeg")

    start = time.perf_counter()
    resp = requests.post(url, files=files, timeout=10)
    elapsed = (time.perf_counter() - start) * 1000
    return resp.status_code, elapsed


def _print_result(i: int, total: int, label: str, status: int, ms: float) -> None:
    ok = "OK " if status == 200 else "ERR"
    print(f"  [{ok}] #{i:>3}/{total}  {label:<30}  {status}  {ms:6.1f} ms")


# ── Simulation modes ──────────────────────────────────────────────────────────

def simulate_single(args: argparse.Namespace) -> None:
    label = f"unknown face" if args.unknown else f"student {args.student_id}"
    print(f"\nSending {args.count} event(s) for {label}  →  {args.server}\n")

    for i in range(1, args.count + 1):
        xml = (
            _build_unmatched_xml(args.camera_ip)
            if args.unknown
            else _build_matched_xml(
                employee_no=str(args.student_id),
                name=f"Student {args.student_id}",
                camera_ip=args.camera_ip,
                similarity=args.similarity,
            )
        )
        try:
            status, ms = _send_event(args.server, xml, include_image=not args.no_image)
            _print_result(i, args.count, label, status, ms)
        except requests.exceptions.ConnectionError:
            print(f"  [ERR] Cannot connect to {args.server} — is the server running?")
            sys.exit(1)

        if args.interval > 0 and i < args.count:
            time.sleep(args.interval)


def simulate_multi_student(args: argparse.Namespace) -> None:
    student_ids = [str(1000 + i) for i in range(args.count)]
    print(f"\nSimulating {args.count} different students arriving  →  {args.server}\n")

    for i, sid in enumerate(student_ids, start=1):
        xml = _build_matched_xml(
            employee_no=sid,
            name=f"Student {sid}",
            camera_ip=args.camera_ip,
            similarity=args.similarity,
        )
        try:
            status, ms = _send_event(args.server, xml, include_image=not args.no_image)
            _print_result(i, args.count, f"student {sid}", status, ms)
        except requests.exceptions.ConnectionError:
            print(f"  [ERR] Cannot connect to {args.server}")
            sys.exit(1)

        if args.interval > 0 and i < args.count:
            time.sleep(args.interval)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Simulate Hikvision ISAPI face-recognition events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--server", default=DEFAULT_SERVER, help="Server base URL (default: %(default)s)")
    p.add_argument("--camera-ip", default=DEFAULT_CAMERA_IP, help="Simulated camera IP in the XML")
    p.add_argument("--student-id", type=int, default=12345, help="Employee/student ID to embed in XML")
    p.add_argument("--similarity", type=float, default=96.5, help="AI match similarity score (0–100)")
    p.add_argument("--unknown", action="store_true", help="Send an unmatched (unknown) face event")
    p.add_argument("--multi-student", action="store_true", help="Send events for N different students")
    p.add_argument("--count", type=int, default=1, help="Number of events to send (default: 1)")
    p.add_argument("--interval", type=float, default=0.5, help="Seconds between events (default: 0.5)")
    p.add_argument("--no-image", action="store_true", help="Omit the JPEG snapshot from the request")
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()

    if args.multi_student:
        simulate_multi_student(args)
    else:
        simulate_single(args)

    print("\nDone.")

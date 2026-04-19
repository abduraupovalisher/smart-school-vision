"""Register, list, and remove cameras without writing SQL by hand.

Usage:
    python -m scripts.register_camera add 192.168.1.100 "Main Entrance"
    python -m scripts.register_camera list
    python -m scripts.register_camera remove 192.168.1.100
    python -m scripts.register_camera rename 192.168.1.100 "North Gate"
"""
import argparse
import ipaddress
import sys

from database import Base, SessionLocal, engine
from models import Camera


def _validate_ip(ip: str) -> str:
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise SystemExit(f"error: '{ip}' is not a valid IP address")
    return ip


def cmd_add(ip: str, name: str) -> int:
    _validate_ip(ip)
    with SessionLocal() as db:
        existing = db.query(Camera).filter(Camera.ip_address == ip).first()
        if existing:
            print(f"error: camera with IP {ip} already registered as '{existing.entrance_name}'")
            print("       use 'rename' to update the entrance name or 'remove' first")
            return 1
        db.add(Camera(ip_address=ip, entrance_name=name))
        db.commit()
        print(f"registered {ip} -> {name!r}")
    return 0


def cmd_list() -> int:
    with SessionLocal() as db:
        cams = db.query(Camera).order_by(Camera.ip_address).all()
    if not cams:
        print("(no cameras registered)")
        return 0
    width = max(len(c.ip_address) for c in cams)
    for c in cams:
        active = "" if c.is_active else "  [inactive]"
        print(f"  {c.ip_address:<{width}}  {c.entrance_name}{active}")
    return 0


def cmd_remove(ip: str) -> int:
    _validate_ip(ip)
    with SessionLocal() as db:
        cam = db.query(Camera).filter(Camera.ip_address == ip).first()
        if not cam:
            print(f"error: no camera registered with IP {ip}")
            return 1
        db.delete(cam)
        db.commit()
        print(f"removed {ip} ({cam.entrance_name!r})")
    return 0


def cmd_rename(ip: str, name: str) -> int:
    _validate_ip(ip)
    with SessionLocal() as db:
        cam = db.query(Camera).filter(Camera.ip_address == ip).first()
        if not cam:
            print(f"error: no camera registered with IP {ip}")
            return 1
        old = cam.entrance_name
        cam.entrance_name = name
        db.commit()
        print(f"renamed {ip}: {old!r} -> {name!r}")
    return 0


def main() -> int:
    Base.metadata.create_all(bind=engine)
    p = argparse.ArgumentParser(description="Manage camera registrations.")
    sub = p.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="register a new camera")
    add.add_argument("ip")
    add.add_argument("name", help="entrance name (quote if it contains spaces)")

    sub.add_parser("list", help="list all registered cameras")

    rm = sub.add_parser("remove", help="remove a camera registration")
    rm.add_argument("ip")

    rn = sub.add_parser("rename", help="rename the entrance for an existing camera")
    rn.add_argument("ip")
    rn.add_argument("name")

    args = p.parse_args()
    if args.cmd == "add":
        return cmd_add(args.ip, args.name)
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "remove":
        return cmd_remove(args.ip)
    if args.cmd == "rename":
        return cmd_rename(args.ip, args.name)
    return 2


if __name__ == "__main__":
    sys.exit(main())

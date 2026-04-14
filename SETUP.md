# Setup & Testing Guide

## Prerequisites

- Python 3.12+ (project was developed on Python 3.14)
- A Hikvision camera with face recognition configured to send ISAPI webhooks *(only needed for live testing)*
- The camera and the server must be on the same network

---

## 1. Initial Setup

```bash
# Clone the repo and enter the directory
git clone <repo-url>
cd smart-school-vision

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Configuration

Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

Key variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./school.db` | SQLAlchemy connection string |
| `SNAPSHOT_DIR` | `data/snapshots` | Directory for saved face images |
| `DEDUP_TTL_SECONDS` | `30` | Seconds before the same student triggers another event |
| `CORS_ORIGINS` | *(empty → allow all)* | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## 3. Running the API Server

```bash
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The server creates the SQLite database and all tables on first startup.

Verify it is healthy:
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

---

## 4. Running the Desktop App

```bash
source venv/bin/activate
python main.py
```

The GUI connects to the same `school.db` database that the API server uses.

---

## 5. Running the Test Suite

```bash
source venv/bin/activate
pytest               # run all tests
pytest -v            # verbose output
pytest tests/test_cache.py          # single file
pytest tests/test_event_processor.py -k "extract"  # single test by keyword
```

All tests use an in-memory SQLite database — no real database or camera needed.

---

## 6. Registering Cameras

Before the server can map camera IPs to entrance names, add a row to the `cameras` table:

```python
# run once from the project root
from database import SessionLocal
from models import Camera

db = SessionLocal()
db.add(Camera(ip_address="192.168.1.100", entrance_name="Main Gate"))
db.commit()
db.close()
```

Or use any SQLite browser (e.g. [DB Browser for SQLite](https://sqlitebrowser.org/)) to insert rows directly.

---

## 7. Configuring the Hikvision Camera

On the camera's web interface:

1. Navigate to **Configuration → Network → Advanced → Integration Protocol**.
2. Enable **Notify Surveillance Center**.
3. Set **Notification Host IP** to the server's IP address.
4. Set **Notification Host Port** to `8000`.
5. Set the HTTP listener path to `/api/webhook`.
6. Enable **Face Recognition** events.

The camera will now POST multipart XML + JPEG events to `POST http://<server-ip>:8000/api/webhook`.

---

## 8. Manually Sending a Test Webhook

With the server running:

```bash
python test_webhook.py
```

This sends a synthetic XML event (student ID `12345`) with a dummy image and prints the response status.

---

## 9. Building the Desktop App as a Standalone Executable

```bash
source venv/bin/activate
pyinstaller --onefile --windowed main.py
# Output: dist/main  (or dist/main.exe on Windows)
```

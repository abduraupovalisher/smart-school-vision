# Setup & Testing Guide

## Prerequisites

- Python 3.12+ (project was developed on Python 3.14)
- A Hikvision camera with face recognition configured to send ISAPI webhooks *(only needed for live testing)*
- The camera and the server must be on the same network

---

## 1. Initial Setup

```bash
git clone <repo-url>
cd smart-school-vision

python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

---

## 2. Configuration

Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./school.db` | SQLAlchemy connection string |
| `SNAPSHOT_DIR` | `data/snapshots` | Directory for saved face images |
| `DEDUP_TTL_SECONDS` | `30` | Seconds before the same student triggers another event |
| `CORS_ORIGINS` | *(empty → allow all)* | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `DIAGNOSTICS_ENABLED` | `0` | Enable `/api/diagnostics/recent` — turn on during camera setup, off in production |
| `DIAGNOSTICS_BUFFER_SIZE` | `100` | How many recent events the diagnostics buffer keeps |

---

## 3. Running the API Server

```bash
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The server creates the SQLite database and all tables on first startup.

```bash
curl http://localhost:8000/health    # → {"status":"ok"}
```

---

## 4. Running the Desktop App

```bash
source venv/bin/activate
python main.py
```

---

## 5. Running the Test Suite

```bash
pytest                              # all default tests (excludes live)
pytest tests/test_cache.py
pytest tests/test_event_processor.py -k "extract"
pytest -m live -s                   # live camera tests (see §8)
```

All default tests use an in-memory SQLite DB — no camera or real DB required.

---

## 6. End-to-End Camera Integration — Step by Step

Follow the steps **in order**. Each step has a verification command; do not
move on until you see the expected output. This is what replaces
"point the camera at a face and hope."

### Step A — Start the server with diagnostics enabled

```bash
DIAGNOSTICS_ENABLED=1 uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Verify:**
```bash
python -m scripts.doctor
```
Expect four `[OK]` lines (database, cameras — may WARN if none yet, snapshot dir, API server).

### Step B — Register the camera's IP in the database

Find the camera's IP (check your router's DHCP table or the camera's display). Then:

```bash
python -m scripts.register_camera add 192.168.1.100 "Main Entrance"
python -m scripts.register_camera list
```

**Why this matters:** without registration, events fall back to entrance `"Unknown Entrance"`. You will not know which door a student used.

### Step C — Configure the camera's ISAPI listener

On the camera's web UI:

1. **Configuration → Network → Advanced → HTTP Listening** *(menu name varies by firmware; also seen as "Alarm Host" or "Notify Surveillance Center")*
2. Set **Destination IP / URL** to the server machine's LAN IP (not `localhost` — the camera cannot reach the server's localhost).
3. Set **Destination Port** to `8000`.
4. Set **URL** to `/api/webhook`.
5. Set protocol to **HTTP** (not HTTPS unless you've set up TLS).
6. Save / Apply.

Then on the camera:

7. **Configuration → Event → Smart Event → Face Capture** (or **Face Recognition** on models with onboard AI): enable the event, set a face library, and under **Linkage Method** tick **Notify Surveillance Center**.
8. Save.

### Step D — Confirm the camera can reach the server

From a machine on the same network as the camera:

```bash
curl http://<server-lan-ip>:8000/health
```

If this fails from the camera's side (e.g. firewall on the server host), the camera can't reach it either. On Windows, allow inbound TCP 8000; on macOS, check System Settings → Network → Firewall.

### Step E — Trigger a face and watch diagnostics in real time

In one terminal:

```bash
# poll the diagnostics endpoint every second
watch -n 1 'curl -s http://localhost:8000/api/diagnostics/recent?limit=10 | python -m json.tool'
# (on Windows PowerShell, use: while(1){ curl http://localhost:8000/api/diagnostics/recent?limit=10; sleep 1 })
```

Walk in front of the camera with an enrolled face. You should see a sequence of stages per event:

1. `stage: webhook_received, ok: true` — camera reached the server and sent XML.
2. `stage: persisted, ok: true, entrance: "Main Entrance", student_id: "..."` — event saved.

**Common failure signatures and fixes:**

| Symptom in diagnostics | Likely cause | Fix |
|---|---|---|
| No events at all | Camera can't reach server | Verify Step D; check firewall; check camera's Notification Host setting |
| `webhook_received, ok: false, error: "no XML part found"` | Camera sending a format the parser doesn't recognise | Capture the raw request with `tcpdump` / Wireshark; update `_XML_MAGIC` logic in `api/routes/isapi.py` |
| `xml_parse, ok: false` | Malformed XML | Same as above — inspect the payload |
| `persisted, ok: true, entrance: "Unknown Entrance"` | Camera IP not registered, or NATed IP differs | Check the `client_ip` in the diagnostic entry and register **that** IP |
| `dedup, skipped: true` | Duplicate within 30s | Expected behaviour; wait for TTL or lower `DEDUP_TTL_SECONDS` for testing |
| `persisted, ok: false` | DB write failed | Check server logs for the exception |

### Step F — Run the live test suite

Once Step E produces the expected stages, run the automated live tests:

```bash
pytest -m live -s
```

Each test prompts you to trigger a specific face in front of the camera; it then polls diagnostics for up to 30s and asserts the outcome. Override the target server with `LIVE_SERVER=http://192.168.1.50:8000`.

### Step G — Turn diagnostics OFF for production

The `/api/diagnostics/recent` endpoint exposes recent student IDs and client IPs. Before leaving the server running unsupervised, unset the flag:

```bash
# restart without DIAGNOSTICS_ENABLED; the endpoint now returns 404
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 7. Camera Management CLI

```bash
python -m scripts.register_camera add 192.168.1.100 "Main Entrance"
python -m scripts.register_camera list
python -m scripts.register_camera rename 192.168.1.100 "North Gate"
python -m scripts.register_camera remove 192.168.1.100
```

---

## 8. Simulating a Camera (No Hardware Required)

```bash
python test_webhook.py
python camera_simulator.py --student-id 12345
python camera_simulator.py --multi-student --count 3
python camera_simulator.py --student-id 1 --count 10 --interval 0   # burst, tests dedup
```

---

## 9. Health Check

```bash
python -m scripts.doctor
python -m scripts.doctor --server http://192.168.1.50:8000
```

Non-zero exit code if any check fails. Good for CI or a post-deploy smoke test.

---

## 10. Building the Desktop App as a Standalone Executable

```bash
source venv/bin/activate
pyinstaller --onefile --windowed main.py
# Output: dist/main  (or dist/main.exe on Windows)
```

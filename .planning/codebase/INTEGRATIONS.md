# External Integrations

**Analysis Date:** 2026-03-05

## APIs & External Services

**None** - This is a self-contained application with no external API dependencies. All processing happens locally.

**Internal API (Backend -> Frontend):**
- FastAPI REST API at `http://localhost:8000`
  - `GET /api/status` - System status (camera, model, FPS, uptime)
  - `GET /api/stream` - MJPEG video stream (multipart/x-mixed-replace)
  - `POST /api/stream/start` - Start camera capture and detection
  - `POST /api/stream/stop` - Stop camera capture and detection
  - `GET /api/alerts` - List violation alerts with thumbnails
  - `DELETE /api/alerts` - Clear all alerts
  - `GET /api/stats` - Session statistics and violation timeline
  - Client: `frontend/src/lib/api.ts` (plain fetch, no HTTP client library)
  - Base URL: `NEXT_PUBLIC_API_URL` env var

## Data Storage

**Databases:**
- None - All data is stored in-memory

**In-Memory State:**
- Alerts stored in `deque(maxlen=50)` (`backend/app/alerts.py`)
- Frame compliance counters (total/compliant frame counts)
- Alert cooldown tracking per violation type
- Current JPEG frame buffer for MJPEG streaming

**File Storage:**
- YOLO model weights: `backend/yolov8n.pt` (local file, not downloaded at runtime)
- No persistent file storage for alerts, frames, or logs

**Caching:**
- None (beyond in-memory frame buffer)

## Authentication & Identity

**Auth Provider:**
- None - No authentication implemented
- CORS configured to allow specified origins (`backend/app/config.py`: `CORS_ORIGINS`)
- All API endpoints are publicly accessible

## Hardware Integrations

**Webcam/Camera:**
- OpenCV VideoCapture via device index (`backend/app/camera.py`)
- Configurable via `VIGILANTE_CAMERA_INDEX` (default: 0)
- Resolution: `VIGILANTE_CAMERA_WIDTH` x `VIGILANTE_CAMERA_HEIGHT` (default: 640x480)
- Threaded capture loop with frame locking
- Docker device passthrough: `/dev/video0` (commented out in `docker-compose.yml`)

**ML Model:**
- YOLOv8 nano model (`yolov8n.pt`) loaded via Ultralytics library
- Supports PPE-specific custom models (detects `safety_glasses`, `no_safety_glasses`, `hardhat`, `no_hardhat`)
- Falls back to generic person detection if model lacks PPE classes (`backend/app/detector.py`)

## Monitoring & Observability

**Error Tracking:**
- None - No error tracking service integrated

**Logs:**
- Python `logging` module (`backend/app/camera.py`, `backend/app/detector.py`, `backend/app/stream.py`)
- Logger per module via `logging.getLogger(__name__)`
- No structured logging or log aggregation configured

## CI/CD & Deployment

**Hosting:**
- Docker Compose (local deployment)
- No cloud hosting configuration detected

**CI Pipeline:**
- None - No `.github/workflows/` or other CI configuration detected

## Environment Configuration

**Required env vars:**
- None strictly required (all have defaults)

**Optional env vars:**
- `NEXT_PUBLIC_API_URL` - Frontend API base URL (default: `http://localhost:8000`)
- `VIGILANTE_CAMERA_INDEX` - Camera device index (default: 0)
- `VIGILANTE_MODEL_PATH` - Path to YOLO weights (default: `yolov8n.pt`)
- `VIGILANTE_CONFIDENCE_THRESHOLD` - Detection confidence (default: 0.5)
- `VIGILANTE_CORS_ORIGINS` - Allowed origins list (default: `["http://localhost:3000"]`)
- `VIGILANTE_ALERT_COOLDOWN_SECONDS` - Alert dedup cooldown (default: 10)

**Secrets location:**
- No secrets required (no external services, no auth)
- `.env` files listed in `.gitignore`

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Video Streaming Protocol

**MJPEG over HTTP:**
- Backend generates MJPEG stream via `StreamingResponse` with `multipart/x-mixed-replace` boundary
- Frontend consumes via `<img>` tag pointing to `/api/stream` endpoint
- Frame rate: ~30 FPS target (0.03s sleep between frames in `backend/app/stream.py`)
- Frames are JPEG-encoded via OpenCV `cv2.imencode`

---

*Integration audit: 2026-03-05*

# Architecture

**Analysis Date:** 2026-03-05

## Pattern Overview

**Overall:** Monolithic client-server with real-time video streaming

**Key Characteristics:**
- Two-tier architecture: Python backend (FastAPI) + TypeScript frontend (Next.js)
- Backend handles all AI/ML processing (YOLO object detection) and exposes a REST + MJPEG streaming API
- Frontend is a thin client that polls REST endpoints and renders an MJPEG stream via `<img>` tag
- No database -- all state is held in-memory (alerts stored in a `deque`, stats computed on the fly)
- Backend uses threading for concurrent camera capture and frame processing
- Communication is strictly HTTP (no WebSockets) -- frontend polls every 2-5 seconds for status/alerts/stats

## Layers

**API Layer (Backend):**
- Purpose: HTTP endpoints for stream control, alerts, stats, and status
- Location: `backend/app/main.py`
- Contains: FastAPI app instance, route handlers, CORS config, service instantiation
- Depends on: `StreamProcessor`, `AlertManager`, `CameraManager`, `SafetyDetector`
- Used by: Frontend via HTTP

**Detection Layer (Backend):**
- Purpose: YOLO model loading and PPE violation detection on video frames
- Location: `backend/app/detector.py`
- Contains: `SafetyDetector` class -- model loading, frame inference, frame annotation with bounding boxes
- Depends on: `backend/app/config.py`, `backend/app/models.py`, `ultralytics` (YOLO), `cv2`
- Used by: `StreamProcessor`

**Camera Layer (Backend):**
- Purpose: Webcam capture via OpenCV in a background thread
- Location: `backend/app/camera.py`
- Contains: `CameraManager` class -- thread-safe frame capture loop
- Depends on: `backend/app/config.py`, `cv2`
- Used by: `StreamProcessor`

**Stream Processing Layer (Backend):**
- Purpose: Orchestrates camera capture, detection, alert generation, and MJPEG output
- Location: `backend/app/stream.py`
- Contains: `StreamProcessor` class -- the central processing pipeline
- Depends on: `CameraManager`, `SafetyDetector`, `AlertManager`
- Used by: API layer (`main.py`)

**Alert Management Layer (Backend):**
- Purpose: Stores alerts with cooldown logic, computes stats and violation timelines
- Location: `backend/app/alerts.py`
- Contains: `AlertManager` class -- in-memory alert storage (`deque` with max 50), cooldown tracking, compliance rate calculation
- Depends on: `backend/app/config.py`, `backend/app/models.py`
- Used by: `StreamProcessor`, API layer

**Domain Models (Backend):**
- Purpose: Core data structures for detections and alerts
- Location: `backend/app/models.py`
- Contains: `Detection` and `Alert` dataclasses
- Used by: `SafetyDetector`, `AlertManager`

**API Schemas (Backend):**
- Purpose: Pydantic response models for API serialization
- Location: `backend/app/schemas.py`
- Contains: `AlertResponse`, `AlertListResponse`, `ClearAlertsResponse`, `StatsResponse`, `ViolationTimelineEntry`
- Used by: API layer

**Configuration (Backend):**
- Purpose: Centralized settings via environment variables
- Location: `backend/app/config.py`
- Contains: `Settings` class (pydantic-settings) with `VIGILANTE_` env prefix
- Used by: All backend layers

**Frontend Pages:**
- Purpose: Next.js App Router pages
- Location: `frontend/src/app/`
- Contains: Monitoring page (`page.tsx`), Dashboard page (`dashboard/page.tsx`), Root layout (`layout.tsx`)
- Depends on: Components, API client

**Frontend Components:**
- Purpose: React UI components for monitoring and dashboard views
- Location: `frontend/src/components/`
- Contains: `VideoFeed`, `AlertPanel`, `AlertCard`, `Controls`, `StatusBar`, `StatsCards`, `ViolationsChart`
- Depends on: `frontend/src/lib/api.ts`, `frontend/src/types/index.ts`

**Frontend API Client:**
- Purpose: HTTP fetch wrappers for backend communication
- Location: `frontend/src/lib/api.ts`
- Contains: Functions for `getStatus`, `getAlerts`, `clearAlerts`, `getStats`, `startStream`, `stopStream`
- Used by: All client components

**Frontend Types:**
- Purpose: TypeScript interfaces mirroring backend response schemas
- Location: `frontend/src/types/index.ts`
- Contains: `Alert`, `SystemStatus`, `SessionStats`, `ViolationTimelineEntry`, `ViolationType`

## Data Flow

**Video Stream Pipeline:**

1. `CameraManager` captures frames from webcam in a background thread (`_capture_loop`) at configured resolution
2. `StreamProcessor._process_loop` retrieves frames, passes them to `SafetyDetector.detect()`
3. `SafetyDetector` runs YOLO inference, returns `Detection` objects (class name, confidence, bounding box)
4. `StreamProcessor` filters violations, calls `AlertManager.add_alert()` for each (with cooldown)
5. `SafetyDetector.annotate_frame()` draws bounding boxes on the frame
6. Annotated frame is JPEG-encoded and stored as `_current_jpeg`
7. `StreamProcessor.generate_mjpeg()` yields JPEG frames as MJPEG multipart response
8. Frontend `<img>` tag consumes the MJPEG stream at `GET /api/stream`

**Alert Flow:**

1. Violations detected by `SafetyDetector` trigger `AlertManager.add_alert()`
2. Cooldown check prevents duplicate alerts for the same violation type within `ALERT_COOLDOWN_SECONDS`
3. Alert includes a base64 JPEG thumbnail (160x120) of the frame
4. Alerts stored in a `deque(maxlen=50)` -- oldest alerts are evicted
5. Frontend `AlertPanel` polls `GET /api/alerts` every 2 seconds
6. `AlertCard` renders each alert with thumbnail, violation label, confidence, and timestamp

**Stats/Dashboard Flow:**

1. `AlertManager.record_frame()` called for every processed frame, tracking compliant vs total frames
2. `GET /api/stats` computes: total violations (alert count), session duration, compliance rate
3. `get_violations_timeline()` aggregates alerts by minute for the timeline chart
4. Frontend `DashboardPage` polls `GET /api/stats` every 5 seconds
5. `StatsCards` renders summary metrics, `ViolationsChart` renders timeline via Recharts

**State Management:**
- Backend: All state is in-memory Python objects (`deque`, `dict`, counters) with `threading.Lock` for thread safety
- Frontend: React `useState` + `useEffect` polling -- no global state management library

## Key Abstractions

**Detection:**
- Purpose: Represents a single YOLO detection result (class, confidence, bounding box)
- Examples: `backend/app/models.py`
- Pattern: Python dataclass, value object

**Alert:**
- Purpose: Represents a PPE violation event with thumbnail and timestamp
- Examples: `backend/app/models.py`
- Pattern: Python dataclass with auto-generated `id` (UUID) and `timestamp`

**StreamProcessor:**
- Purpose: Orchestrator that ties camera, detector, and alerts together
- Examples: `backend/app/stream.py`
- Pattern: Composed service with dependency injection via constructor. Central coordinator of the processing pipeline.

**Settings:**
- Purpose: Type-safe configuration from environment variables
- Examples: `backend/app/config.py`
- Pattern: Pydantic `BaseSettings` with `VIGILANTE_` env prefix. Singleton instance exported as `settings`.

## Entry Points

**Backend Server:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn.run("app.main:app")` or `uvicorn app.main:app` from CLI
- Responsibilities: Creates FastAPI app, instantiates all services, defines all route handlers

**Frontend App:**
- Location: `frontend/src/app/layout.tsx` (root layout), `frontend/src/app/page.tsx` (monitoring page)
- Triggers: Next.js App Router
- Responsibilities: Renders app shell with navigation, delegates to page components

**Docker Compose:**
- Location: `docker-compose.yml`
- Triggers: `docker compose up`
- Responsibilities: Orchestrates backend (port 8000) and frontend (port 3000) containers

## Error Handling

**Strategy:** Minimal -- errors are mostly silently caught or logged

**Patterns:**
- Backend: `CameraManager.start()` raises `RuntimeError` if camera cannot open. Detection returns empty list if model is not loaded. Logging via Python `logging` module.
- Frontend: All API calls wrapped in try/catch with empty catch blocks (errors silently ignored). Components show fallback UI when data is `null` (e.g., "Feed indisponivel", "--" placeholders).
- No structured error responses from the API -- no error schema or error codes defined.

## Cross-Cutting Concerns

**Logging:** Python `logging` module used in backend (`camera.py`, `detector.py`, `stream.py`). No structured logging. Frontend has no logging.

**Validation:** Pydantic models validate API response shapes in `backend/app/schemas.py`. Frontend TypeScript types mirror backend schemas but no runtime validation on API responses.

**Authentication:** None. All endpoints are publicly accessible. CORS configured to allow `http://localhost:3000`.

**Thread Safety:** Backend uses `threading.Lock` in `CameraManager`, `AlertManager`, and `StreamProcessor` to protect shared mutable state.

---

*Architecture analysis: 2026-03-05*

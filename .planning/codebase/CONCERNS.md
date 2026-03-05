# Codebase Concerns

**Analysis Date:** 2026-03-05

## Tech Debt

**No Persistent Storage - All Data Is In-Memory:**
- Issue: `AlertManager` stores alerts in a Python `deque` and stats as simple counters. All data is lost on every backend restart. There is no database, no file persistence, no external storage of any kind.
- Files: `backend/app/alerts.py`
- Impact: Production unusable for audit/compliance purposes. Historical violation data cannot be reviewed after a restart. Session stats reset to zero.
- Fix approach: Introduce a database (SQLite for MVP, PostgreSQL for production). Create a persistence layer for alerts, stats, and session history. Add an ORM (SQLAlchemy or Tortoise) and migration tooling (Alembic).

**Hardcoded YOLO Model Weights Committed to Git:**
- Issue: `backend/yolov8n.pt` (6.3 MB binary) is committed directly in the repository. The `.gitignore` only ignores `backend/models/*.pt`, but the file lives at `backend/yolov8n.pt`.
- Files: `backend/yolov8n.pt`, `.gitignore`
- Impact: Repository bloat. Every clone downloads the model binary. Versioning model weights in git is an anti-pattern. The generic `yolov8n` model does not contain PPE-specific classes (see detector fallback logic).
- Fix approach: Add `backend/*.pt` to `.gitignore`. Use a download script or DVC for model management. Store trained PPE model weights in cloud storage (S3/GCS).

**Fallback Detection Is Misleading:**
- Issue: When the loaded YOLO model lacks PPE-specific classes (which is the case with the shipped `yolov8n.pt`), the detector treats every detected "person" as a `no_hardhat` violation. This produces false positives for every person in frame.
- Files: `backend/app/detector.py` (lines 70-74)
- Impact: The system generates fake violations in its default configuration. Users see alerts that do not correspond to real safety violations. This undermines trust in the system.
- Fix approach: Either ship a trained PPE model, or disable alerting when using the fallback model and show a clear "demo mode" indicator in the UI.

**Frontend API Client Has No Error Handling:**
- Issue: Every function in `frontend/src/lib/api.ts` calls `fetch()` without checking `res.ok` or handling non-200 responses. If the backend returns a 500, the frontend silently parses the error body as valid JSON and uses it as data.
- Files: `frontend/src/lib/api.ts` (all functions)
- Impact: Silent failures. Corrupted state in UI components. No user feedback when the backend is down or returns errors.
- Fix approach: Create a wrapper around `fetch` that checks `res.ok`, throws typed errors, and provides consistent error handling. Components already have `try/catch` blocks but they silently swallow errors.

**Silent Error Swallowing in Frontend Components:**
- Issue: Multiple components catch errors and do nothing: `DashboardPage` (line 17: `catch {}`), `AlertPanel` (line 43: `catch {}`), `StatusBar` (line 13: `.catch(() => setStatus(null))`).
- Files: `frontend/src/app/dashboard/page.tsx`, `frontend/src/components/AlertPanel.tsx`, `frontend/src/components/StatusBar.tsx`
- Impact: No error monitoring or observability. Users see stale data with no indication that polling has failed. Debugging production issues is impossible without error tracking.
- Fix approach: Add error state to components. Display user-facing error messages (e.g., "Backend unavailable"). Integrate an error tracking service (Sentry or similar).

**Compliance Rate Calculation Bug:**
- Issue: The backend returns `compliance_rate` as a 0-100 float (e.g., `85.0` for 85%). The `StatsCards` component multiplies it by 100 again: `(s.compliance_rate * 100).toFixed(1)%`, producing values like `8500.0%`.
- Files: `backend/app/alerts.py` (line 96: `self._compliant_frames / self._total_frames * 100.0`), `frontend/src/components/StatsCards.tsx` (line 33: `(s.compliance_rate * 100).toFixed(1)`)
- Impact: Dashboard displays incorrect compliance rate (e.g., 8500% instead of 85%).
- Fix approach: Either change the backend to return a 0-1 decimal, or remove the `* 100` in `StatsCards.tsx`. Standardize the contract in the shared types.

## Known Bugs

**AudioContext Created But Never Reused:**
- Symptoms: `AlertPanel.playNotification()` creates a new `AudioContext` every time it is called (the `if (!audioRef.current)` guard checks `audioRef` but never assigns to it). Each invocation spawns a new audio context, which browsers limit.
- Files: `frontend/src/components/AlertPanel.tsx` (lines 15-26)
- Trigger: Enable sound notifications, then wait for multiple alerts.
- Workaround: None currently. After enough alerts, the browser may refuse to create new AudioContexts.

## Security Considerations

**CORS Configured With Wildcard Methods and Headers:**
- Risk: The backend allows all HTTP methods (`["*"]`) and all headers (`["*"]`) from the configured origins. While origins are restricted, the wildcard methods/headers are overly permissive.
- Files: `backend/app/main.py` (lines 22-28)
- Current mitigation: Origins are restricted to `["http://localhost:3000"]` by default via `settings.CORS_ORIGINS`.
- Recommendations: Explicitly list allowed methods (`GET`, `POST`, `DELETE`) and headers. Add CORS origin configuration for production deployment.

**No Authentication or Authorization:**
- Risk: All API endpoints are publicly accessible. Anyone who can reach the backend can start/stop the camera, view the video stream, and clear alerts.
- Files: `backend/app/main.py` (all endpoints)
- Current mitigation: None. Acceptable for local development only.
- Recommendations: Add API key authentication at minimum. For production, implement proper auth (JWT tokens, OAuth, or session-based).

**No Rate Limiting on Endpoints:**
- Risk: The `/api/stream/start` endpoint initializes the camera and loads the YOLO model. Repeated calls could exhaust resources. The `/api/stream` endpoint keeps a connection open indefinitely.
- Files: `backend/app/main.py` (lines 46-51, 54-57)
- Current mitigation: `StreamProcessor.start()` returns early if already running.
- Recommendations: Add rate limiting middleware. Limit concurrent MJPEG stream connections.

**Backend Binds to 0.0.0.0 by Default:**
- Risk: The backend listens on all network interfaces, making the camera stream accessible to anyone on the local network.
- Files: `backend/app/config.py` (line 9: `HOST: str = "0.0.0.0"`)
- Current mitigation: None.
- Recommendations: Default to `127.0.0.1` for development. Use `0.0.0.0` only in Docker or when explicitly configured.

## Performance Bottlenecks

**YOLO Inference Runs on Every Frame With No Skip Logic:**
- Problem: The processing loop in `StreamProcessor._process_loop()` runs YOLO inference on every single frame captured by the camera. YOLO inference is CPU-intensive (or GPU-intensive).
- Files: `backend/app/stream.py` (lines 89-122)
- Cause: No frame skipping, no inference throttling. If the camera produces 30 FPS, the system attempts 30 YOLO inferences per second.
- Improvement path: Add configurable frame skip (e.g., run inference every 3rd frame). Use the last detection result for intermediate frames. Add GPU/CUDA detection and configuration.

**Thumbnail Generation on Every Alert:**
- Problem: `AlertManager._make_thumbnail()` resizes and JPEG-encodes a frame for every alert. With the fallback model generating false positives for every detected person, this creates unnecessary CPU load.
- Files: `backend/app/alerts.py` (lines 36-41)
- Cause: Thumbnail generation happens synchronously in the processing loop.
- Improvement path: Move thumbnail generation to a background thread or async task. Cache thumbnails.

**Base64-Encoded Thumbnails in API Responses:**
- Problem: Each alert includes a full base64-encoded JPEG thumbnail in the JSON response. With 50 alerts (the max), the `/api/alerts` response can be several hundred KB.
- Files: `backend/app/alerts.py` (line 41), `backend/app/schemas.py` (line 13), `frontend/src/components/AlertCard.tsx` (line 29)
- Cause: No separate image endpoint. Thumbnails are inlined in the JSON payload.
- Improvement path: Serve thumbnails as separate image endpoints (`/api/alerts/{id}/thumbnail`). Store thumbnail paths instead of base64 data in the alert model.

**Polling-Based Architecture Without WebSockets:**
- Problem: The frontend polls `/api/alerts` every 2 seconds and `/api/stats` every 5 seconds and `/api/status` every 2 seconds. Each page load creates multiple recurring HTTP requests.
- Files: `frontend/src/components/AlertPanel.tsx` (line 47), `frontend/src/components/StatusBar.tsx` (line 16), `frontend/src/app/dashboard/page.tsx` (line 23)
- Cause: No WebSocket or SSE implementation.
- Improvement path: Implement WebSocket connections for real-time alert push and status updates. This eliminates polling overhead and provides instant alert delivery.

## Fragile Areas

**Thread Safety in AlertManager:**
- Files: `backend/app/alerts.py`
- Why fragile: `_is_on_cooldown()` reads `self._cooldowns` without holding the lock, while `add_alert()` writes to `self._cooldowns` under the lock. `record_frame()` modifies `_total_frames` and `_compliant_frames` without any lock. `get_stats()` reads `_alerts`, `_total_frames`, and `_compliant_frames` without a lock.
- Safe modification: Acquire `self._lock` in all methods that read or write shared state, or use `threading.RLock` to allow re-entrant locking. Alternatively, use atomic counters.
- Test coverage: No tests exist for any concurrent access patterns.

**Global Singletons in main.py:**
- Files: `backend/app/main.py` (lines 30-33)
- Why fragile: `camera`, `detector`, `alert_manager`, and `stream_processor` are module-level singletons. This makes testing impossible without monkeypatching. State persists across requests and there is no cleanup on shutdown.
- Safe modification: Use FastAPI dependency injection with `Depends()`. Add lifespan events for startup/shutdown cleanup.
- Test coverage: No tests exist.

**MJPEG Stream Generator Has No Connection Cleanup:**
- Files: `backend/app/stream.py` (lines 79-87)
- Why fragile: `generate_mjpeg()` runs in an infinite loop with `time.sleep(0.03)`. If the client disconnects, the generator continues running until the `_running` flag is set to False (which only happens on explicit stop). Multiple connected clients each get their own generator.
- Safe modification: Add client disconnect detection. Use `asyncio` generators with proper cancellation. Track active connections.
- Test coverage: No tests exist.

## Scaling Limits

**In-Memory Alert Storage (50 Alert Cap):**
- Current capacity: Maximum 50 alerts stored in `deque(maxlen=50)`.
- Limit: Older alerts are silently discarded. No historical record.
- Scaling path: Persist alerts to a database. Remove the `maxlen` cap or make it configurable.

**Single Camera Support Only:**
- Current capacity: One camera via `cv2.VideoCapture(settings.CAMERA_INDEX)`.
- Limit: Cannot monitor multiple areas or cameras simultaneously.
- Scaling path: Refactor `CameraManager` to support multiple camera instances. Add camera registration endpoints.

**Single-Process Architecture:**
- Current capacity: One uvicorn worker processing one video stream.
- Limit: Cannot scale horizontally. The MJPEG stream and YOLO inference share the same process.
- Scaling path: Separate the video processing pipeline from the API server. Use a message queue (Redis/RabbitMQ) for alert distribution.

## Dependencies at Risk

**Pinned to yolov8n (Generic Model):**
- Risk: The shipped model (`yolov8n.pt`) is a generic COCO object detection model, not a PPE detection model. The system cannot fulfill its core purpose without a custom-trained model.
- Impact: All detections in the default configuration are false positives (every person flagged as "no_hardhat").
- Migration plan: Train a YOLOv8 model on a PPE dataset (e.g., hard hat, safety glasses). Update `settings.MODEL_PATH` to point to the trained model.

**ultralytics Dependency:**
- Risk: The `ultralytics` package is large (pulls in PyTorch, CUDA bindings, etc.) and has frequent breaking changes in its API.
- Impact: Heavy Docker images. Slow CI builds. Potential API breakage on updates.
- Migration plan: Pin to a specific version. Consider ONNX Runtime for inference in production to reduce dependency footprint.

## Missing Critical Features

**No Test Suite:**
- Problem: Zero test files exist anywhere in the project. No unit tests, no integration tests, no E2E tests. No test framework is configured for the backend. No test dependencies in `requirements.txt` or `pyproject.toml`.
- Blocks: Safe refactoring. CI/CD pipeline setup. Confidence in deployments.

**No CI/CD Pipeline:**
- Problem: No GitHub Actions, no GitLab CI, no pipeline configuration of any kind.
- Blocks: Automated testing, linting, and deployment.

**No Logging Configuration:**
- Problem: Python `logging` is used in backend modules but never configured (no handler, no formatter, no level set). Default Python logging suppresses everything below WARNING.
- Blocks: Debugging production issues. Observability.

**No Error Monitoring/Observability:**
- Problem: No Sentry, no structured logging, no metrics collection, no health check endpoint.
- Blocks: Understanding production behavior. Detecting and diagnosing issues.

**No Database or Persistence Layer:**
- Problem: All state is in-memory. No database schema, no migrations, no ORM.
- Blocks: Multi-session analytics. Audit trails. Compliance reporting.

**No Input Validation on API Endpoints:**
- Problem: `POST /api/stream/start` and `POST /api/stream/stop` accept no parameters but also have no request validation. `DELETE /api/alerts` has no confirmation or soft-delete.
- Blocks: Safe multi-user operation. Audit trails for who started/stopped monitoring.

## Test Coverage Gaps

**Backend - Zero Coverage:**
- What's not tested: Every module. `SafetyDetector.detect()`, `CameraManager` thread lifecycle, `AlertManager` cooldown logic, `StreamProcessor` pipeline, all FastAPI endpoints.
- Files: `backend/app/main.py`, `backend/app/detector.py`, `backend/app/camera.py`, `backend/app/stream.py`, `backend/app/alerts.py`
- Risk: Any refactoring or feature addition could break existing functionality silently. The thread safety issues in `AlertManager` cannot be validated without concurrent tests.
- Priority: High

**Frontend - Zero Coverage:**
- What's not tested: All components, API client functions, polling logic, error handling paths.
- Files: `frontend/src/lib/api.ts`, `frontend/src/components/*.tsx`, `frontend/src/app/**/*.tsx`
- Risk: UI regressions. Broken API integration. The compliance rate display bug would have been caught by a simple snapshot or unit test.
- Priority: High

---

*Concerns audit: 2026-03-05*

# Phase 1: Foundation - Research

**Researched:** 2026-03-05
**Domain:** Python/FastAPI backend (YOLOv8 object detection, threading, OpenCV) + Next.js 14 frontend (Tailwind, React state)
**Confidence:** HIGH

## Summary

Phase 1 addresses 8 requirements across three areas: (1) fixing stop/start crash and thread safety bugs in the existing streaming pipeline, (2) swapping the generic YOLOv8 model for the 6-class PPE model with Portuguese labels, and (3) adding configurable EPI selection via API and frontend panel.

The codebase is compact and well-structured. The backend uses FastAPI with global singleton instances (`CameraManager`, `SafetyDetector`, `StreamProcessor`, `AlertManager`) running detection in a daemon thread. The frontend is Next.js 14 with client components and Tailwind CSS. There are no automated tests. The `best.pt` model has been verified to load successfully with Ultralytics 8.4.21 and exposes 6 classes: `{0: 'Gloves', 1: 'Vest', 2: 'goggles', 3: 'helmet', 4: 'mask', 5: 'safety_shoe'}`.

The primary risks are the MJPEG generator lifecycle (BUG-01) where the generator keeps running after `stop()` is called, and the lack of FPS throttling in the processing loop which causes unnecessarily high CPU usage.

**Primary recommendation:** Fix the MJPEG generator orphan and thread lifecycle first, then swap the model and class mappings, then add the EPI configuration layer on top.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- EPI Selection Panel: Sidebar on monitoring page, left of video feed. All 6 EPIs unchecked by default. Live toggle (changes take effect immediately). Zero EPIs allowed. Selection persists across stop/start.
- Label Display Format: Full Portuguese name + confidence percentage on bounding boxes (e.g., "Capacete 92%"). Only show detected (present) EPIs. Only show active (user-selected) EPIs on stream. Single green color for all detected EPI bounding boxes.
- Stop/Start Behavior: Stopping resets all alerts, stats, and timeline. EPI selection persists. Status indicator: "Monitorando" with green dot when active, "Parado" when stopped. Stopped state shows placeholder: "Clique em Iniciar para comecar o monitoramento".
- Alert Panel: Portuguese name + colored badge (e.g., "Capacete ausente"). Each alert card shows EPI name, timestamp, confidence %, frame thumbnail. Newest first. Last 50 alerts with scroll.
- Alert format: "Capacete ausente" / "Luvas ausentes" (Portuguese with gendered adjective)

### Claude's Discretion
- Exact sidebar width and responsive behavior
- Alert card styling details and badge colors
- Status indicator design
- Placeholder styling when stopped
- Thread safety fix approach for BUG-01/BUG-02
- FPS capping implementation (20-30 FPS)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUG-01 | Fix stop/start crash -- resolve camera lifecycle and orphaned MJPEG generator issues | MJPEG generator analysis below; `generate_mjpeg()` loops on `self._running` but StreamingResponse holds generator reference after stop; camera `_capture_loop` exits cleanly but generator does not |
| BUG-02 | Fix thread safety issues in stream processing pipeline | Thread analysis below; `_current_jpeg` access is locked but `_running` flag is not atomic; `record_frame` counters have no lock protection |
| MODL-01 | Swap generic yolov8n.pt for PPE-specific best.pt (6 classes) | Model verified to load with Ultralytics 8.4.21; class names confirmed: Gloves, Vest, goggles, helmet, mask, safety_shoe |
| MODL-02 | Map model classes to Portuguese labels | Class mapping dictionary defined in Architecture Patterns section |
| MODL-03 | Cap detection FPS at 20-30 for better accuracy per frame | FPS throttling pattern documented below using `time.sleep()` in process loop |
| CONF-01 | API endpoint to get/set active EPIs | FastAPI endpoint pattern with Pydantic model; uses in-memory set on StreamProcessor |
| CONF-02 | Frontend checkbox panel to select which EPIs to monitor | React component pattern with local state synced to backend; sidebar layout |
| CONF-03 | Backend filters detections to only generate alerts for active EPIs | Filter applied in `_process_loop` after `detect()` call |

</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| FastAPI | >=0.109.0 | REST API | Already in requirements.txt |
| Ultralytics | 8.4.21 | YOLOv8 inference | Installed in venv, verified working with best.pt |
| OpenCV (headless) | >=4.9.0 | Frame capture, annotation, JPEG encoding | Already installed |
| pydantic-settings | >=2.1.0 | Configuration management | Already installed |
| Next.js | 14.2.35 | Frontend framework | Already installed |
| React | ^18 | UI components | Already installed |
| Tailwind CSS | ^3.4.1 | Styling | Already installed |

### No New Libraries Needed

This phase requires zero new dependencies. All work is refactoring existing code and adding new endpoints/components using the existing stack.

## Architecture Patterns

### Backend Class Mapping (MODL-01 + MODL-02)

The model's raw class names must map to Portuguese display labels and internal IDs:

```python
# Source: Verified from model.names output + CONTEXT.md decisions
# Model class index -> internal key -> Portuguese label
EPI_CLASSES: dict[int, str] = {
    0: "luvas",
    1: "colete",
    2: "protecao_ocular",
    3: "capacete",
    4: "mascara",
    5: "calcado_seguranca",
}

EPI_LABELS_PT: dict[str, str] = {
    "luvas": "Luvas",
    "colete": "Colete",
    "protecao_ocular": "Protecao ocular",
    "capacete": "Capacete",
    "mascara": "Mascara",
    "calcado_seguranca": "Calcado de seguranca",
}

# For alert messages -- gendered "ausente/ausentes" per CONTEXT.md
EPI_ALERT_LABELS: dict[str, str] = {
    "luvas": "Luvas ausentes",
    "colete": "Colete ausente",
    "protecao_ocular": "Protecao ocular ausente",
    "capacete": "Capacete ausente",
    "mascara": "Mascara ausente",
    "calcado_seguranca": "Calcado de seguranca ausente",
}
```

**Key insight:** The current code uses `PPE_CLASSES`, `VIOLATION_CLASSES`, and `COMPLIANT_CLASSES` sets in `detector.py`. Phase 1 model only detects *presence* of EPIs (not absence). The concept of "violation" shifts: in Phase 1, a missing EPI is inferred by its absence from detections, not from a "no_X" class. Full absence-based infraction logic is Phase 3 (INFR-*). For Phase 1, alerts are generated when an active EPI is not detected in a frame with a person present -- but this logic needs to be simple (cooldown-based, not state-machine).

**Important model difference:** The new 6-class model detects PPE items directly (Gloves, Vest, etc.), NOT "no_gloves" / "no_vest" violation classes. The old model had `no_hardhat` / `no_safety_glasses` violation classes. This fundamentally changes the alert logic:
- Old: Detection of `no_hardhat` = violation
- New: Detection of `capacete` = compliant; *absence* of detection = potential violation

For Phase 1, alerts should only fire when an active EPI is not detected AND a person is visible. However, this model does NOT detect "person" -- it only detects PPE items. This means Phase 1 cannot reliably determine "person present but missing EPI X" without additional logic. The simplest approach: if ANY EPIs are detected in a frame, we know a person is present, and we can check which active EPIs are missing. If zero EPIs are detected, we cannot determine if a person is there, so no alert.

### EPI Configuration State (CONF-01 + CONF-03)

```python
# In-memory state on StreamProcessor or a dedicated config object
# Set of active EPI keys; empty by default per CONTEXT.md
_active_epis: set[str] = set()  # e.g., {"capacete", "luvas"}
```

The API needs two endpoints:
- `GET /api/config/epis` -- returns all 6 EPIs with their active/inactive state
- `POST /api/config/epis` -- accepts list of active EPI keys, updates state

The filter is applied in `_process_loop`: after `detect()` returns all detections, filter to only those whose class key is in `_active_epis`. Only filtered detections get annotated on frame and checked for alerts.

### MJPEG Generator Fix (BUG-01)

**Root cause analysis:** `generate_mjpeg()` is a Python generator that loops on `self._running`. When `StreamingResponse` holds a reference to this generator and `stop()` sets `_running = False`, the generator exits its loop on the next iteration. However, the `StreamingResponse` may still be held by an active HTTP connection. If the client reconnects and calls `/api/stream` again, a new generator is created while the old connection may still be lingering.

**The real crash scenario:** When `stop()` is called:
1. `_running = False` -- generator loop exits
2. `_thread.join()` -- waits for process loop to end
3. `camera.stop()` -- releases capture

Then `start()` is called:
1. `camera.start()` -- opens new capture
2. New process thread starts
3. But any old `/api/stream` connection still holds an orphaned generator that now reads stale `_current_jpeg`

**Fix approach:** Add a generation counter or epoch ID. When `stop()` is called, increment the epoch. The generator checks epoch on each iteration and exits if it mismatches. Additionally, `stop()` should clear `_current_jpeg` to `b""` so any lingering generator sends empty frames until it exits.

### Thread Safety Fix (BUG-02)

**Issues identified in current code:**

1. **`_running` flag is not thread-safe.** It's a plain `bool` set from the main thread and read from the processing thread. Python's GIL makes simple attribute reads/writes atomic for built-in types, so this is technically safe in CPython, but `threading.Event` is the idiomatic and correct pattern.

2. **`AlertManager.record_frame()` counter updates are not locked.** `_total_frames` and `_compliant_frames` are incremented in the processing thread but read in the main thread via `get_stats()`. These should be protected by the existing `_lock`.

3. **`AlertManager._cooldowns` access.** `_is_on_cooldown()` reads `_cooldowns` without lock, `add_alert()` writes under lock. Should be consistent.

4. **`StreamProcessor._fps` and `_start_time`** are written in the process thread and read from the main thread without lock protection.

**Fix:** Use `threading.Event` for `_running`. Extend existing locks to cover counter reads/writes. Add lock to FPS/uptime reads.

### FPS Throttling (MODL-03)

```python
# In _process_loop, add frame timing
TARGET_FPS = 25  # middle of 20-30 range
FRAME_INTERVAL = 1.0 / TARGET_FPS

while self._running:
    loop_start = time.monotonic()

    # ... detection and encoding ...

    elapsed = time.monotonic() - loop_start
    sleep_time = FRAME_INTERVAL - elapsed
    if sleep_time > 0:
        time.sleep(sleep_time)
```

### Frontend Layout Restructure (CONF-02)

Current layout in `page.tsx`:
```
Header (title + controls)
StatusBar
Grid: [VideoFeed 2/3] [AlertPanel 1/3]
```

New layout per CONTEXT.md:
```
Header (title + controls + status indicator)
Grid: [EPIPanel sidebar] [VideoFeed] [AlertPanel]
```

The sidebar goes LEFT of video. This means the grid changes from `grid-cols-3` to a 4-column or flex layout: narrow sidebar (EPI checkboxes) + wide video + alert panel.

### VideoFeed State Management

The `VideoFeed` component needs to handle three states:
1. **Stopped:** Show dark placeholder with "Clique em Iniciar para comecar o monitoramento"
2. **Running:** Show MJPEG stream with `<img>` tag
3. **Error:** Show error message

The component needs to know monitoring state. Currently `VideoFeed` is stateless regarding monitoring. It needs to receive `isRunning` as a prop or poll status.

### Anti-Patterns to Avoid

- **Do not create a WebSocket connection for EPI config.** REST POST is sufficient since config changes are infrequent. The processing loop picks up the new `_active_epis` set on the next frame.
- **Do not use React Context or state management library for EPI state.** Simple `useState` + API calls are sufficient. The source of truth is the backend.
- **Do not implement person detection for Phase 1.** The 6-class model does not detect "person". Absence-of-EPI logic should be kept simple: only flag missing EPIs when at least one EPI is detected (proxy for person presence).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe stop signal | Custom boolean flag | `threading.Event` | `.is_set()` is thread-safe by design, `.wait(timeout)` replaces `time.sleep` |
| MJPEG boundary framing | Custom byte concat | Existing pattern is fine | The `--frame\r\n` boundary pattern is correct |
| Model class name lookup | String matching/parsing | `model.names[class_id]` -> lookup dict | Ultralytics provides class names directly from model metadata |
| Pydantic request validation | Manual JSON parsing | Pydantic `BaseModel` for POST body | Already using pydantic-settings; request validation is free |
| Responsive sidebar | CSS media queries | Tailwind responsive classes (`lg:`, `md:`) | Already using Tailwind throughout |

## Common Pitfalls

### Pitfall 1: MJPEG Generator Orphan on Stop/Start
**What goes wrong:** After calling stop then start, the old MJPEG generator from a previous `/api/stream` request may still be alive on an open HTTP connection, causing the browser to display stale frames or crash.
**Why it happens:** `StreamingResponse` holds the generator; the HTTP connection may not close immediately.
**How to avoid:** Use an epoch/generation counter. Each generator checks the epoch; if it changed, generator yields nothing and exits. On `stop()`, increment epoch and clear `_current_jpeg`.
**Warning signs:** Browser shows frozen last frame after restart; multiple generators accumulate memory.

### Pitfall 2: Missing Lock on AlertManager Counters
**What goes wrong:** `_total_frames` and `_compliant_frames` may show inconsistent values in stats endpoint.
**Why it happens:** Incremented in processing thread without lock, read in request thread.
**How to avoid:** Use `_lock` context manager for both writes and reads of counters.
**Warning signs:** Compliance rate shows impossible values (>100% or negative).

### Pitfall 3: FPS Cap Too Tight
**What goes wrong:** If target FPS is set to exactly 20 and detection takes variable time, actual FPS fluctuates below target.
**Why it happens:** `time.sleep()` is not precise; OS scheduling adds jitter.
**How to avoid:** Target 25 FPS (middle of 20-30 range). Measure actual FPS and log if consistently below 20.
**Warning signs:** FPS counter shows < 20 despite light detection load.

### Pitfall 4: EPI Config Race Condition
**What goes wrong:** If EPI config is updated while a frame is being processed, the frame may use a mix of old and new config.
**Why it happens:** The set is read in the processing thread and written from the API thread.
**How to avoid:** Use a lock around `_active_epis` reads/writes, or use `frozenset` assignment (atomic in CPython due to GIL, but lock is safer for clarity).
**Warning signs:** Intermittent frame showing deselected EPI right after config change.

### Pitfall 5: Alert Logic Without Person Detection
**What goes wrong:** System generates "EPI missing" alerts on empty frames (no person visible).
**Why it happens:** Model only detects PPE items, not persons. If no detections at all, cannot distinguish "no person" from "person without any EPE."
**How to avoid:** Only generate "missing EPI" alerts when at least one EPI class is detected in the frame (proxy: someone is there wearing something). If zero detections, skip alert generation entirely.
**Warning signs:** Constant "missing" alerts on empty room.

### Pitfall 6: VideoFeed img Tag Caching
**What goes wrong:** Browser may cache the MJPEG stream URL and not reconnect after stop/start.
**Why it happens:** `<img src={STREAM_URL}>` is the same URL every time.
**How to avoid:** Append a cache-busting query param when starting (e.g., `?t={Date.now()}`). Or remount the `<img>` element by changing its React key.
**Warning signs:** After restart, video shows stale last frame or nothing.

## Code Examples

### EPI Config Pydantic Models (CONF-01)

```python
# backend/app/schemas.py additions
class EPIItem(BaseModel):
    key: str           # e.g., "capacete"
    label: str         # e.g., "Capacete"
    active: bool

class EPIConfigResponse(BaseModel):
    epis: list[EPIItem]

class EPIConfigRequest(BaseModel):
    active_epis: list[str]  # list of EPI keys to activate
```

### Threading Event Pattern (BUG-01 + BUG-02)

```python
# Replace self._running = False with threading.Event
class StreamProcessor:
    def __init__(self, ...):
        self._stop_event = threading.Event()
        self._epoch = 0  # generation counter

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set()

    def start(self) -> None:
        self._stop_event.clear()
        self._epoch += 1
        # ... start camera, thread

    def stop(self) -> None:
        self._stop_event.set()
        # ... join thread, stop camera

    def generate_mjpeg(self) -> Generator[bytes, None, None]:
        epoch = self._epoch  # capture current epoch
        while not self._stop_event.is_set() and epoch == self._epoch:
            frame = self.get_jpeg_frame()
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            self._stop_event.wait(0.03)  # replaces time.sleep, exits immediately on stop
```

### EPI Checkbox Panel Component (CONF-02)

```tsx
// frontend/src/components/EPIPanel.tsx
"use client";

import { useState, useEffect } from "react";

interface EPIItem {
  key: string;
  label: string;
  active: boolean;
}

export default function EPIPanel() {
  const [epis, setEpis] = useState<EPIItem[]>([]);

  // Fetch initial config, then POST on change
  // Each checkbox toggles the EPI and immediately POSTs to backend
}
```

### Detection Filter in Process Loop (CONF-03)

```python
# In _process_loop after detect()
detections = self._detector.detect(frame)

# Filter to only active EPIs
with self._epi_lock:
    active = self._active_epis.copy()

if active:
    filtered = [d for d in detections if d.class_name in active]
else:
    filtered = []  # no EPIs selected = no detections shown

# Annotate with filtered detections only
annotated = self._detector.annotate_frame(frame, filtered)
```

## State of the Art

| Old Approach (current code) | New Approach (Phase 1) | Impact |
|------------------------------|------------------------|--------|
| `yolov8n.pt` generic model | `best.pt` 6-class PPE model | Detection of actual PPE items instead of generic objects |
| `PPE_CLASSES = {"safety_glasses", "no_safety_glasses", ...}` | `EPI_CLASSES = {0: "luvas", 1: "colete", ...}` | Complete class mapping rewrite |
| Violation = detecting "no_X" class | Violation = active EPI not detected | Fundamentally different alert trigger logic |
| `self._running = False` boolean | `threading.Event` + epoch counter | Proper thread lifecycle management |
| No FPS cap (runs as fast as possible) | 25 FPS target with sleep | Consistent frame rate, lower CPU usage |
| Fixed 2-class alert labels | Configurable 6-class Portuguese labels | User-selected EPI monitoring |

## Open Questions

1. **Alert logic for missing EPIs without person detection**
   - What we know: Model detects PPE items (present), not their absence. No "person" class.
   - What's unclear: How to reliably determine "person present but missing EPI X" with only PPE detection classes.
   - Recommendation: Use "at least one EPI detected" as proxy for person presence. If any active EPI is found, check which other active EPIs are missing and alert on those. This is imperfect but workable for Phase 1. Phase 2 tracking (STAB-*) and Phase 3 infraction logic (INFR-*) will refine this.

2. **Alert cooldown per-EPI or global**
   - What we know: Current `ALERT_COOLDOWN_SECONDS = 10` is per violation_type. This pattern extends naturally to per-EPI-key cooldown.
   - Recommendation: Keep per-EPI-key cooldown at 10 seconds. Works with existing AlertManager pattern.

3. **Model confidence thresholds per class**
   - What we know: Current global threshold is 0.5. Model mAP varies by class (Gloves ~0.69, Vest ~0.90, safety_shoe ~0.64).
   - Recommendation: Keep global 0.5 for Phase 1. Per-class thresholds are v2 scope (EXPT-02).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), not yet chosen (frontend) |
| Config file | None -- needs creation in Wave 0 |
| Quick run command | `cd backend && .venv/bin/python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && .venv/bin/python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUG-01 | Stop/start does not crash; MJPEG generator exits on stop | unit | `.venv/bin/python -m pytest tests/test_stream.py::test_stop_start_lifecycle -x` | Wave 0 |
| BUG-02 | Thread-safe counter access; no race conditions | unit | `.venv/bin/python -m pytest tests/test_stream.py::test_thread_safety -x` | Wave 0 |
| MODL-01 | best.pt loads and returns 6 classes | unit | `.venv/bin/python -m pytest tests/test_detector.py::test_model_loads_ppe_classes -x` | Wave 0 |
| MODL-02 | Detection results use Portuguese labels | unit | `.venv/bin/python -m pytest tests/test_detector.py::test_portuguese_labels -x` | Wave 0 |
| MODL-03 | Process loop respects FPS cap | unit | `.venv/bin/python -m pytest tests/test_stream.py::test_fps_throttle -x` | Wave 0 |
| CONF-01 | GET/POST /api/config/epis returns/accepts EPI config | integration | `.venv/bin/python -m pytest tests/test_api.py::test_epi_config_endpoints -x` | Wave 0 |
| CONF-02 | Frontend EPI panel renders checkboxes (manual verification) | manual-only | N/A -- visual UI component | N/A |
| CONF-03 | Only active EPIs appear in detections/alerts | unit | `.venv/bin/python -m pytest tests/test_stream.py::test_epi_filter -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && .venv/bin/python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && .venv/bin/python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/__init__.py` -- package init
- [ ] `backend/tests/conftest.py` -- shared fixtures (mock model, mock camera frames)
- [ ] `backend/tests/test_detector.py` -- covers MODL-01, MODL-02
- [ ] `backend/tests/test_stream.py` -- covers BUG-01, BUG-02, MODL-03, CONF-03
- [ ] `backend/tests/test_api.py` -- covers CONF-01
- [ ] `backend/pytest.ini` or `pyproject.toml` [tool.pytest] section
- [ ] Framework install: `pip install pytest pytest-asyncio httpx` (httpx for FastAPI TestClient)

## Sources

### Primary (HIGH confidence)
- **Model verification** -- Direct `YOLO('best.pt').names` output: `{0: 'Gloves', 1: 'Vest', 2: 'goggles', 3: 'helmet', 4: 'mask', 5: 'safety_shoe'}` with Ultralytics 8.4.21
- **Codebase analysis** -- Direct reading of all backend (detector.py, stream.py, camera.py, main.py, alerts.py, config.py, models.py, schemas.py) and frontend (page.tsx, Controls.tsx, VideoFeed.tsx, AlertPanel.tsx, AlertCard.tsx, StatusBar.tsx, api.ts, types/index.ts) source files

### Secondary (MEDIUM confidence)
- **Threading patterns** -- Python `threading.Event` is standard library, well-documented behavior for stop signals
- **MJPEG generator lifecycle** -- Based on FastAPI StreamingResponse behavior with Python generators

### Tertiary (LOW confidence)
- **Alert logic for missing EPIs** -- The "proxy person detection via any-EPI-detected" approach is a pragmatic workaround; may need refinement based on real-world testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified working
- Architecture: HIGH -- thorough codebase analysis, clear modification paths
- Bug analysis: HIGH -- root causes identified through code reading
- Alert logic for missing EPIs: MEDIUM -- workaround approach, not battle-tested
- Pitfalls: MEDIUM -- based on code analysis and Python threading knowledge

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable stack, no fast-moving dependencies)

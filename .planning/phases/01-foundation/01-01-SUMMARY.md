---
phase: 01-foundation
plan: 01
subsystem: streaming
tags: [threading, opencv, fps-throttling, test-infrastructure, pytest]

# Dependency graph
requires: []
provides:
  - Thread-safe StreamProcessor with epoch-based generator lifecycle
  - FPS-throttled processing loop at 25 FPS
  - Thread-safe AlertManager with lock-protected counters
  - CameraManager with threading.Event stop signal
  - Test infrastructure with mock camera, detector, and alert manager fixtures
  - Test scaffolds for Plans 02-03 (MODL-01, MODL-02, CONF-01)
affects: [01-02, 01-03]

# Tech tracking
tech-stack:
  added: [pytest, pytest-asyncio, httpx]
  patterns: [threading.Event for lifecycle, epoch counter for generator invalidation, FPS throttling via Event.wait]

key-files:
  created:
    - backend/tests/__init__.py
    - backend/tests/conftest.py
    - backend/tests/test_stream.py
    - backend/tests/test_alerts.py
    - backend/tests/test_detector.py
    - backend/tests/test_api.py
  modified:
    - backend/app/stream.py
    - backend/app/camera.py
    - backend/app/alerts.py
    - backend/pyproject.toml

key-decisions:
  - "threading.Event replaces bool _running for immediate stop response via Event.wait"
  - "Epoch counter invalidates stale MJPEG generators across stop/start cycles"
  - "TARGET_FPS=25 with Event.wait-based sleep for interruptible throttling"

patterns-established:
  - "Lifecycle pattern: threading.Event + epoch counter for clean stop/start"
  - "Lock-protected reads: all shared state (fps, uptime, counters) accessed under _lock"
  - "Test fixture pattern: mock_camera, mock_detector, alert_manager, stream_processor in conftest.py"

requirements-completed: [BUG-01, BUG-02, MODL-03]

# Metrics
duration: 3min
completed: 2026-03-05
---

# Phase 1 Plan 01: Test Infrastructure + Stream Stability Summary

**Thread-safe StreamProcessor with epoch-based generator lifecycle, FPS throttling at 25 FPS, and full test scaffolding for phase**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-05T22:20:48Z
- **Completed:** 2026-03-05T22:23:41Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Test infrastructure with pytest fixtures for mock camera, detector, and alert manager
- Stop/start crash fixed via threading.Event and epoch counter for generator invalidation
- FPS throttled from unlimited (~3300 FPS) to ~25 FPS with Event.wait-based sleep
- AlertManager record_frame, get_stats, and _is_on_cooldown lock-protected for thread safety

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test infrastructure and test scaffolds** - `065cf31` (test)
2. **Task 2: Fix stop/start crash, thread safety, and FPS throttling** - `9732431` (fix)

_TDD approach: Task 1 wrote RED tests, Task 2 made them GREEN._

## Files Created/Modified
- `backend/tests/conftest.py` - Shared fixtures: mock_camera, mock_detector, alert_manager, stream_processor
- `backend/tests/test_stream.py` - Tests for BUG-01, BUG-02, MODL-03 (lifecycle, thread safety, FPS cap)
- `backend/tests/test_alerts.py` - Tests for AlertManager thread safety
- `backend/tests/test_detector.py` - Placeholder scaffolds for MODL-01, MODL-02
- `backend/tests/test_api.py` - Placeholder scaffold for CONF-01
- `backend/tests/__init__.py` - Package marker
- `backend/pyproject.toml` - Added pytest config
- `backend/app/stream.py` - threading.Event + epoch + FPS throttling
- `backend/app/camera.py` - threading.Event for lifecycle
- `backend/app/alerts.py` - Lock-protected counters and cooldown checks

## Decisions Made
- Used `threading.Event` instead of bool `_running` for immediate stop response via `Event.wait(timeout)` replacing `time.sleep`
- Epoch counter approach for invalidating stale MJPEG generators -- simpler than tracking individual generator references
- `TARGET_FPS=25` as module-level constant (not configurable via Settings yet -- that is Plan 02 scope)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Stream lifecycle is stable: stop/start, epoch-based generator invalidation, FPS cap all tested
- Test infrastructure ready for Plans 02 and 03 with placeholder scaffolds
- AlertManager thread safety ensures concurrent detection and stats reads are safe

---
*Phase: 01-foundation*
*Completed: 2026-03-05*

---
phase: 01-foundation
plan: 02
subsystem: detection
tags: [yolov8, ppe-detection, portuguese-labels, epi-config, api, filtering]

# Dependency graph
requires:
  - phase: 01-01
    provides: Thread-safe StreamProcessor with test infrastructure and mock fixtures
provides:
  - 6-class PPE detection with Portuguese labels via best.pt model
  - EPI configuration API (GET/POST /api/config/epis)
  - EPI filter in stream processing pipeline (active-only detections)
  - Missing-EPI alert generation with Portuguese messages
  - AlertManager.reset_session() for stop cleanup
affects: [01-03]

# Tech tracking
tech-stack:
  added: []
  patterns: [EPI class mapping dicts for i18n, active-set filter in process loop, absence-based alerts with person proxy]

key-files:
  created: []
  modified:
    - backend/app/detector.py
    - backend/app/config.py
    - backend/app/schemas.py
    - backend/app/main.py
    - backend/app/stream.py
    - backend/app/alerts.py
    - backend/tests/test_detector.py
    - backend/tests/test_api.py
    - backend/tests/test_stream.py

key-decisions:
  - "EPI_CLASSES maps model class_id integers to Portuguese keys, not English names"
  - "Empty active_epis set means zero detections pass through (not all)"
  - "Person proxy: at least one active EPI detected triggers missing-EPI alert check"
  - "stop() calls reset_session() to clear alerts, cooldowns, and counters"

patterns-established:
  - "EPI mapping pattern: EPI_CLASSES (id->key), EPI_LABELS_PT (key->display), EPI_ALERT_LABELS (key->alert)"
  - "Filter pattern: copy active set under lock, filter detections, annotate only filtered"
  - "Absence alert: detected_keys vs active set diff generates missing-EPI alerts"

requirements-completed: [MODL-01, MODL-02, CONF-01, CONF-03]

# Metrics
duration: 5min
completed: 2026-03-05
---

# Phase 1 Plan 02: PPE Model + EPI Config Summary

**6-class PPE detection with best.pt, Portuguese labels on bounding boxes, EPI config API, and active-EPI filter in stream pipeline**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T22:26:09Z
- **Completed:** 2026-03-05T22:31:08Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Swapped generic YOLOv8 for 6-class PPE model (best.pt) with Portuguese label mapping
- GET/POST /api/config/epis endpoints for EPI selection with validation
- EPI filter in stream process loop: only active EPIs shown in annotations and alerts
- Missing active EPIs trigger Portuguese alerts (e.g., "Capacete ausente") when person proxy detected
- All 23 backend tests pass

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1 RED: Failing tests for PPE model and EPI config API** - `3a2f348` (test)
2. **Task 1 GREEN: PPE model swap, Portuguese labels, EPI config API** - `a67a7cc` (feat)
3. **Task 2 RED: Failing tests for EPI filter and missing-EPI alerts** - `b2ff97f` (test)
4. **Task 2 GREEN: Wire EPI filter into stream processing and alerts** - `f8ba366` (feat)

## Files Created/Modified
- `backend/app/detector.py` - EPI_CLASSES/EPI_LABELS_PT/EPI_ALERT_LABELS mappings, detect() maps class_id to Portuguese key, annotate_frame() uses green + Portuguese labels
- `backend/app/config.py` - MODEL_PATH changed from yolov8n.pt to best.pt
- `backend/app/schemas.py` - EPIItem, EPIConfigResponse, EPIConfigRequest Pydantic models
- `backend/app/main.py` - GET/POST /api/config/epis endpoints with key validation
- `backend/app/stream.py` - active_epis property, EPI filter in _process_loop, missing-EPI alert logic, reset on stop
- `backend/app/alerts.py` - reset_session() method for full state cleanup
- `backend/tests/test_detector.py` - 7 tests for model loading, Portuguese labels, annotation
- `backend/tests/test_api.py` - 4 tests for EPI config endpoints
- `backend/tests/test_stream.py` - 6 new tests for EPI filter and missing-EPI alerts

## Decisions Made
- EPI_CLASSES maps integer class_ids to Portuguese keys internally (not English model names) -- simpler than double mapping
- Empty active_epis = zero detections pass through, treating it as "nothing monitored" rather than "monitor everything"
- Person proxy pattern: if at least one active EPI is detected, check for missing ones; if zero detected, assume no person in frame
- stop() calls reset_session() to clear all alert state per CONTEXT.md decision

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test reads alerts before stop() since reset_session clears them**
- **Found during:** Task 2 (EPI filter GREEN phase)
- **Issue:** Tests read alerts after stop(), but stop() now calls reset_session() which clears alerts
- **Fix:** Moved alert reads before stop() in test assertions
- **Files modified:** backend/tests/test_stream.py
- **Verification:** All 23 tests pass
- **Committed in:** f8ba366 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test timing fix necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PPE detection pipeline complete: model loads, detects 6 classes, maps to Portuguese
- EPI config API ready for frontend to consume
- Stream pipeline filters by active EPIs and generates Portuguese alerts
- Plan 03 (frontend integration) can now wire up EPI selection UI and display Portuguese labels

---
*Phase: 01-foundation*
*Completed: 2026-03-05*

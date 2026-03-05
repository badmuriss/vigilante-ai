# Phase 1: Foundation - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix stability bugs (stop/start crash, thread safety), swap generic YOLOv8 model for 6-class PPE model (`best.pt`), add configurable EPI selection with Portuguese labels, and working stop/start lifecycle. Detection stability (tracking, smoothing) and infraction logic are separate phases.

</domain>

<decisions>
## Implementation Decisions

### EPI Selection Panel
- Sidebar on the monitoring page, left of the video feed
- All 6 EPIs unchecked by default — user must explicitly select which to monitor
- Live toggle — EPI selection changes take effect immediately while monitoring runs
- Zero EPIs allowed — can start monitoring with none selected (stream shows video, no alerts)
- EPI selection persists across stop/start (does not reset)

### Label Display Format
- Full Portuguese name + confidence percentage on bounding boxes (e.g., "Capacete 92%")
- Only show detected (present) EPIs on the video stream — missing EPIs only in alert panel
- Only show active (user-selected) EPIs on the stream — unselected EPIs filtered from video too
- Single green color for all detected EPI bounding boxes (no per-type color coding in Phase 1)

### Stop/Start Behavior
- Stopping monitoring resets all alerts, stats, and timeline (each session starts fresh)
- EPI selection persists across stop/start
- Status indicator on stream area: "Monitorando" with green dot when active, "Parado" when stopped
- Stopped state shows placeholder with message: "Clique em Iniciar para comecar o monitoramento"

### Alert Panel
- Portuguese name + colored badge format (e.g., "Capacete ausente" with warning icon)
- Each alert card shows: EPI name, timestamp, confidence %, and frame thumbnail snapshot
- Alerts ordered newest first (most recent at top)
- Show last 50 alerts with scroll — older alerts drop off

### Claude's Discretion
- Exact sidebar width and responsive behavior
- Alert card styling details and badge colors
- Status indicator design
- Placeholder styling when stopped
- Thread safety fix approach for BUG-01/BUG-02
- FPS capping implementation (20-30 FPS as decided in project init)

</decisions>

<specifics>
## Specific Ideas

- Alert format: "Capacete ausente" / "Luvas ausentes" (Portuguese with gendered adjective)
- Video placeholder when stopped: dark area with instructional text
- Sidebar layout similar to the ASCII mockup: compact checkbox list with EPI names

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SafetyDetector` (backend/app/detector.py): Core detection class — needs PPE_CLASSES remapped from hardhat/safety_glasses to the 6 new classes
- `AlertManager` (backend/app/alerts.py): Already captures frame thumbnails and manages alert cooldown
- `StreamProcessor` (backend/app/stream.py): Processing loop with MJPEG generator — needs lifecycle fix
- `CameraManager` (backend/app/camera.py): Camera lifecycle with thread-safe frame access
- `Settings` (backend/app/config.py): Pydantic-settings with env prefix — extend for EPI config
- `Controls.tsx`: Existing Iniciar/Parar buttons — add EPI checkboxes alongside
- `AlertCard.tsx` / `AlertPanel.tsx`: Existing alert components — adapt for Portuguese EPI names
- `StatusBar.tsx`: Exists but only shows backend status — extend for monitoring state indicator
- `api.ts`: API client functions — add EPI config endpoints

### Established Patterns
- Backend: FastAPI with global singleton instances (camera, detector, alert_manager, stream_processor)
- Frontend: Next.js 14 with "use client" components, Tailwind CSS for styling
- Communication: REST API with fetch, no state management library
- Threading: Daemon threads with locks for frame access

### Integration Points
- New API endpoints needed: GET/POST `/api/config/epis` for EPI selection
- `SafetyDetector.detect()` needs to accept active EPI filter
- `StreamProcessor._process_loop()` needs EPI filter passed to detection and annotation
- Frontend monitoring page layout needs restructuring for sidebar

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-05*

# Roadmap: Vigilante.AI

## Overview

Transform Vigilante.AI from a generic YOLOv8 detection system into a reliable 6-class PPE compliance monitor with configurable EPI selection, stable zone-based tracking, and per-EPI non-accumulative infraction logic. The build follows a strict dependency chain: stable model foundation, then persistent tracking across frames, then intelligent infraction logic on top of tracking data.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Fix bugs, swap to 6-class PPE model, add configurable EPI selection
- [ ] **Phase 2: Detection Stability and Tracking** - Add object tracking and temporal smoothing for reliable per-person detection
- [ ] **Phase 3: Infraction Logic and Alerts** - Per-zone per-EPI state machine with non-accumulative infraction rules

## Phase Details

### Phase 1: Foundation
**Goal**: Users have a stable system running the 6-class PPE model with Portuguese labels, configurable EPI selection, and working stop/start lifecycle
**Depends on**: Nothing (first phase)
**Requirements**: BUG-01, BUG-02, MODL-01, MODL-02, MODL-03, CONF-01, CONF-02, CONF-03
**Success Criteria** (what must be TRUE):
  1. User can stop and restart monitoring without the system crashing or freezing
  2. Video stream shows bounding boxes for detected PPE items from the 6-class model (Luvas, Colete, Protecao ocular, Capacete, Mascara, Calcado de seguranca) with Portuguese labels
  3. User can check/uncheck EPIs in a frontend panel and only selected EPIs appear in detection results and alerts
  4. Stream runs at 20-30 FPS without frame drops or thread-safety-related errors
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Test infrastructure + fix stop/start crash, thread safety, FPS throttling (BUG-01, BUG-02, MODL-03)
- [ ] 01-02-PLAN.md — Swap to 6-class PPE model, Portuguese labels, EPI config API, backend filter (MODL-01, MODL-02, CONF-01, CONF-03)
- [ ] 01-03-PLAN.md — Frontend EPI panel, layout restructure, video states, alert cards (CONF-02)

### Phase 2: Detection Stability and Tracking
**Goal**: Detections are stable across frames with persistent person zones, eliminating flickering and false positives on non-person objects
**Depends on**: Phase 1
**Requirements**: STAB-01, STAB-02, STAB-03
**Success Criteria** (what must be TRUE):
  1. A person standing still in frame maintains a consistent tracking zone across at least 30 consecutive seconds without ID reassignment
  2. Detection labels for a stationary person do not flicker (appear/disappear) between consecutive frames
  3. Objects that are not people (chairs, posters, equipment) do not generate PPE detection zones or alerts
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Infraction Logic and Alerts
**Goal**: Each person-zone tracks per-EPI compliance state independently, generating exactly the right number of infractions without spam
**Depends on**: Phase 2
**Requirements**: INFR-01, INFR-02, INFR-03, INFR-04, INFR-05
**Success Criteria** (what must be TRUE):
  1. A person who never wears a required EPI generates exactly 1 infraction per missing EPI type (not accumulating over time)
  2. A person who puts on an EPI and then removes it generates a new infraction at the moment of removal
  3. A person missing multiple EPIs simultaneously (e.g., no goggles and no helmet) sees separate alerts for each missing EPI in the alerts panel
  4. Infraction counts in the dashboard accurately reflect the state-machine logic (no duplicates, no missed transitions)
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/3 | Not started | - |
| 2. Detection Stability and Tracking | 0/2 | Not started | - |
| 3. Infraction Logic and Alerts | 0/2 | Not started | - |

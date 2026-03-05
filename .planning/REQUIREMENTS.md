# Requirements: Vigilante.AI

**Defined:** 2026-03-05
**Core Value:** Detectar com precisao quando um trabalhador remove ou nao usa EPIs selecionados e registrar cada infracao de forma clara e individual.

## v1 Requirements

### Bug Fixes

- [ ] **BUG-01**: Fix stop/start crash — resolve camera lifecycle and orphaned MJPEG generator issues
- [ ] **BUG-02**: Fix thread safety issues in stream processing pipeline

### Model Integration

- [ ] **MODL-01**: Swap generic `yolov8n.pt` for PPE-specific `best.pt` (6 classes: Gloves, Vest, goggles, helmet, mask, safety_shoe)
- [ ] **MODL-02**: Map model classes to Portuguese labels (Luvas, Colete, Protecao ocular, Capacete, Mascara, Calcado de seguranca)
- [ ] **MODL-03**: Cap detection FPS at 20-30 for better accuracy per frame

### Configuration

- [ ] **CONF-01**: API endpoint to get/set active EPIs (which of the 6 classes to monitor)
- [ ] **CONF-02**: Frontend checkbox panel to select which EPIs to monitor
- [ ] **CONF-03**: Backend filters detections to only generate alerts for active EPIs

### Detection Stability

- [ ] **STAB-01**: Add object tracking (ByteTrack via supervision) for persistent IDs across frames
- [ ] **STAB-02**: Add temporal smoothing (DetectionsSmoother) to eliminate detection flickering
- [ ] **STAB-03**: Eliminate false positives on non-person objects via tracking and confidence thresholds

### Infraction Logic

- [ ] **INFR-01**: Per-zone per-EPI state machine (UNKNOWN → MISSING → WEARING → REMOVED)
- [ ] **INFR-02**: Non-accumulative infraction: count only 1 if person never wore EPI (no spam)
- [ ] **INFR-03**: New infraction each time person puts on EPI and then removes it
- [ ] **INFR-04**: Independent infraction tracking per EPI type (missing goggles + missing helmet = 2 separate infractions)
- [ ] **INFR-05**: Display separate alerts for each missing EPI in the alerts panel

## v2 Requirements

### Analytics

- **ANLT-01**: Per-EPI compliance breakdown in dashboard
- **ANLT-02**: Severity indicators based on infraction frequency

### Export

- **EXPT-01**: CSV export of infraction history
- **EXPT-02**: Per-class confidence threshold configuration

### Performance

- **PERF-01**: Docker production optimization (multi-stage, resource limits)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom model training | Using pre-trained HF model; training requires dataset and GPU |
| Multi-camera support | Single webcam is sufficient for current use case |
| Database persistence | In-memory state is sufficient for now |
| Mobile app | Web-first approach |
| Push notifications (email/SMS) | Not needed for real-time monitoring workflow |
| Person re-identification across sessions | Beyond scope of spatial zone tracking |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 1 | Pending |
| BUG-02 | Phase 1 | Pending |
| MODL-01 | Phase 1 | Pending |
| MODL-02 | Phase 1 | Pending |
| MODL-03 | Phase 1 | Pending |
| CONF-01 | Phase 1 | Pending |
| CONF-02 | Phase 1 | Pending |
| CONF-03 | Phase 1 | Pending |
| STAB-01 | Phase 2 | Pending |
| STAB-02 | Phase 2 | Pending |
| STAB-03 | Phase 2 | Pending |
| INFR-01 | Phase 3 | Pending |
| INFR-02 | Phase 3 | Pending |
| INFR-03 | Phase 3 | Pending |
| INFR-04 | Phase 3 | Pending |
| INFR-05 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 after roadmap creation*

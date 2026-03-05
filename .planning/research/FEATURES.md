# Feature Research

**Domain:** PPE Detection / Safety Monitoring System (configurable multi-class)
**Researched:** 2026-03-05
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Configurable PPE selection panel** | Every competitor (Protex AI, Visionify, viAct) lets users choose which equipment to monitor. Without this, the system is rigid and unusable for different environments. | MEDIUM | Checkbox UI for 6 classes (Luvas, Colete, Protecao ocular, Capacete, Mascara, Calcado de seguranca). Backend must filter detections to only selected EPIs. Current system hardcodes `VIOLATION_CLASSES`. |
| **Per-EPI-type violation tracking** | Users need to know *which* equipment is missing, not just "violation detected". If someone lacks goggles AND helmet, that is 2 distinct violations. | MEDIUM | Current `AlertManager` tracks by `violation_type` string but the detector only outputs 2 classes. New model has 6 classes. Each missing EPI = separate alert with its own cooldown/state. |
| **Stable detection with debounce/smoothing** | Flickering detections (detected one frame, missing next) destroy trust. Users immediately lose confidence in a system that "cries wolf". Industry standard is a verification period before triggering. | HIGH | Visionify uses a "brief verification period to confirm violations before triggering alerts". Implement temporal smoothing: require N consecutive frames of non-compliance before flagging. This directly addresses the PROJECT.md requirement to fix detection instability. |
| **Non-accumulative infraction logic** | If a worker never puts on a helmet, that is 1 infraction, not 500 (one per frame). A *new* infraction only when equipment is removed after being worn. | MEDIUM | This is a state machine per person per EPI type: UNKNOWN -> MISSING (1 infraction) -> WEARING -> MISSING_AGAIN (new infraction). Current cooldown-based approach is insufficient -- need true state tracking. |
| **Real-time annotated video feed** | Seeing bounding boxes on live video with color-coded compliance/violation is the core UX. Users need visual confirmation the AI is working. | LOW | Already exists. Needs update to show 6-class labels in Portuguese with per-class color coding. |
| **Alert feed with thumbnails** | Supervisors need a scrollable list of recent violations with snapshot images, timestamps, and violation type. | LOW | Already exists (`AlertPanel` + `AlertCard`). Needs expansion to show EPI type labels in Portuguese and handle higher alert volume from 6 classes. |
| **Session statistics dashboard** | Total violations, compliance rate, session duration, violations-over-time chart. Basic metrics for "how is this shift going?". | LOW | Already exists (`StatsCards` + `ViolationsChart`). Needs enhancement to break down stats per EPI type. |
| **Start/stop monitoring controls** | Ability to start and stop detection. Must not crash on restart. | LOW | Already exists but has a bug where stop+start causes freezing. Must fix camera/thread lifecycle. |
| **Portuguese-language UI** | Target users are Brazilian workers/supervisors. English class names are confusing. | LOW | Straightforward label mapping. Apply to all UI surfaces: alerts, dashboard, configuration panel, video annotations. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required for MVP, but add clear value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Per-EPI compliance breakdown in dashboard** | Most simple PPE systems show aggregate "violations count". Breaking down compliance rate per equipment type (e.g., "Capacete: 95%, Luvas: 62%") gives supervisors actionable insight about *which* training is needed. | MEDIUM | Add per-EPI counters to `get_stats()`. Frontend: bar chart or table showing compliance per EPI type. |
| **Confidence threshold per EPI type** | Model accuracy varies by class (Vest ~0.90 mAP vs Safety shoe ~0.64 mAP). Letting the system use different confidence thresholds per class reduces false positives for weaker detections. | LOW | Per-class threshold config in backend. Useful because shoe/glove detection is inherently less reliable than helmet/vest. |
| **Visual alert severity indicators** | Color-code alerts by how many EPIs are missing simultaneously. 1 missing = yellow, 2+ missing = red. Helps supervisors prioritize. | LOW | Simple UI logic based on concurrent violations for same detection frame. |
| **Violation evidence export** | Export violation log (CSV/JSON) with timestamps, types, and thumbnail references. Useful for compliance audits and shift reports. | LOW | Serialize `AlertManager._alerts` to CSV. Low effort, high value for compliance documentation. |
| **Detection zone overlay** | Draw a region-of-interest on the video feed so detection only applies within that zone. Prevents false positives from background objects/people outside the work area. | HIGH | Requires frontend drawing tool + backend mask filtering on detection coordinates. Addresses the false positive problem from PROJECT.md. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems. Deliberately NOT building these.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Per-worker identity tracking** | "I want to know *who* violated, not just *that* someone violated" | Requires face recognition or badge detection, introduces privacy/LGPD concerns, massive complexity increase, and the current model has no person-ID capability. | Track violations by *event* (timestamp + type + thumbnail). The thumbnail provides visual identification without biometric processing. |
| **Multi-camera support** | "We have 3 cameras on the floor" | Multiplies resource consumption, requires camera management UI, synchronization logic, and the system runs on a single machine with one webcam. | Build solid single-camera experience first. Architecture should not preclude multi-camera later, but do not build it now. |
| **Persistent database storage** | "We need history across sessions" | Adds infrastructure complexity (DB setup, migrations, backup). Current scope is session-based monitoring. In-memory state is explicitly acceptable per PROJECT.md. | Keep in-memory. Add CSV export for users who need records. Database is a future milestone, not this one. |
| **SMS/email/WhatsApp notifications** | "Alert me on my phone when violations happen" | External notification infrastructure, rate limiting, credential management, delivery guarantees. Overkill for a webcam-based local monitoring setup. | On-screen alerts with optional browser notifications (Notification API) are sufficient for a supervisor sitting at the monitoring station. |
| **Custom model training pipeline** | "Let me train on my own PPE types" | Massive scope: data collection UI, training infrastructure, model versioning, GPU requirements. Explicitly out of scope in PROJECT.md. | Use the pre-trained 6-class model. 6 classes cover the vast majority of PPE scenarios. |
| **Real-time audio alarms** | "Play a siren when violation detected" | Annoying in practice, causes alert fatigue rapidly. Workers learn to ignore constant alarms. | Visual alerts on dashboard. Browser notification for tab-away scenarios. |

## Feature Dependencies

```
[Configurable PPE Selection Panel]
    |
    +--requires--> [6-class Model Integration]
    |                   |
    |                   +--requires--> [Portuguese Label Mapping]
    |
    +--enables---> [Per-EPI Violation Tracking]
    |                   |
    |                   +--requires--> [Non-accumulative Infraction Logic]
    |                   |
    |                   +--enables---> [Per-EPI Compliance Breakdown]
    |
    +--enables---> [Detection Smoothing/Debounce]

[Detection Smoothing/Debounce]
    +--requires--> [6-class Model Integration]
    +--addresses-> [False Positive Reduction]

[Start/Stop Bug Fix]
    +--independent (no dependencies, should be done first)

[Violation Evidence Export]
    +--requires--> [Per-EPI Violation Tracking]
```

### Dependency Notes

- **Configurable PPE Selection requires 6-class Model Integration:** Cannot offer EPI checkboxes without the model that detects those 6 classes. Model swap is the foundational step.
- **Per-EPI Violation Tracking requires Non-accumulative Infraction Logic:** The state machine (worn -> removed = new infraction) must be implemented per EPI type, not as a global counter.
- **Detection Smoothing requires 6-class Model:** Smoothing logic depends on the actual detection classes being tracked. Must be built after model integration.
- **Start/Stop Bug Fix is independent:** Thread lifecycle bug can and should be fixed before any feature work to establish a stable base.

## MVP Definition

### Launch With (v1 -- this milestone)

Minimum viable configurable PPE detection system.

- [ ] **6-class model integration** -- Foundation. Without this, nothing else works.
- [ ] **Start/stop bug fix** -- System must be stable before adding features.
- [ ] **Portuguese label mapping** -- Target users need Portuguese. Applied across all surfaces.
- [ ] **Configurable PPE selection panel** -- Core requirement. Checkboxes to select which of 6 EPIs to monitor.
- [ ] **Per-EPI violation tracking** -- Each missing EPI = distinct alert. Independent tracking per EPI type.
- [ ] **Non-accumulative infraction logic** -- State machine: 1 infraction if never worn; new infraction only on remove-after-wear.
- [ ] **Detection smoothing/debounce** -- Require N consecutive non-compliant frames before alerting. Eliminates flicker.
- [ ] **False positive reduction** -- Filter detections to person-associated regions. Reduce spurious detections.

### Add After Validation (v1.x)

Features to add once core detection is solid.

- [ ] **Per-EPI compliance breakdown in dashboard** -- Once per-EPI tracking works, surface the data in charts.
- [ ] **Per-class confidence thresholds** -- Tune thresholds per EPI based on real-world accuracy observations.
- [ ] **Violation evidence export (CSV)** -- Low effort, enables compliance documentation.
- [ ] **Visual alert severity indicators** -- Color-coded alert urgency based on violation count.

### Future Consideration (v2+)

Features to defer until this milestone is stable.

- [ ] **Detection zone overlay** -- ROI drawing tool to limit detection area. Addresses false positives more robustly.
- [ ] **Browser push notifications** -- Notification API for tab-away scenarios.
- [ ] **Multi-camera support** -- Only if single-camera is proven and there is demand.
- [ ] **Persistent storage (database)** -- When session-based is insufficient for user needs.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 6-class model integration | HIGH | MEDIUM | P1 |
| Start/stop bug fix | HIGH | LOW | P1 |
| Portuguese label mapping | HIGH | LOW | P1 |
| Configurable PPE selection panel | HIGH | MEDIUM | P1 |
| Per-EPI violation tracking | HIGH | MEDIUM | P1 |
| Non-accumulative infraction logic | HIGH | HIGH | P1 |
| Detection smoothing/debounce | HIGH | HIGH | P1 |
| False positive reduction | HIGH | MEDIUM | P1 |
| Per-EPI compliance breakdown | MEDIUM | LOW | P2 |
| Per-class confidence thresholds | MEDIUM | LOW | P2 |
| Violation evidence export | MEDIUM | LOW | P2 |
| Visual alert severity | LOW | LOW | P2 |
| Detection zone overlay | MEDIUM | HIGH | P3 |
| Browser notifications | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for this milestone
- P2: Should have, add when core is stable
- P3: Nice to have, future milestone

## Competitor Feature Analysis

| Feature | Protex AI | Visionify | viAct.ai | Our Approach |
|---------|-----------|-----------|----------|--------------|
| Equipment types detected | 5+ (helmets, vests, goggles, masks, gloves) | 15+ types | 10+ types | 6 classes via pre-trained HuggingFace model |
| Configurable per-zone rules | Yes (rule builder per zone) | Yes (zone-specific requirements) | Yes (zone-based monitoring) | Simpler: global checkbox selection of which EPIs to monitor. No zones for now. |
| Violation verification delay | Not specified | Yes ("brief verification period") | Not specified | Temporal smoothing with N-frame threshold |
| Alert channels | Dashboard + integrations | Dashboard + SMS + WhatsApp + Teams + email | Dashboard + email + SMS | Dashboard only (browser-based) |
| Compliance reporting | Trend analysis, corrective action tracking | Analytics dashboard, usage patterns | Heatmaps, zone-wise charts | Session stats, per-EPI breakdown, CSV export |
| Camera support | Multiple (enterprise CCTV) | Multiple (RTSP) | Multiple (IP cameras) | Single webcam (OpenCV) |
| Deployment | Cloud/edge | Cloud/edge | Cloud/edge | Local Docker (single machine) |

**Positioning:** Vigilante.AI is not competing with enterprise solutions. It is a focused, self-hosted, single-camera PPE monitoring tool. The differentiator is simplicity: plug in a webcam, select your EPIs, and monitor. No cloud account, no CCTV integration, no enterprise sales process.

## Sources

- [Protex AI - PPE Detection Product](https://www.protex.ai/product/ppe-detection)
- [Visionify - PPE Compliance Detection](https://visionify.ai/ppe-compliance)
- [viAct.ai - PPE Detection](https://www.viact.ai/ppedetection)
- [Tentosoft - PPE Detection System Guide 2025](https://www.tentosoft.com/blogs/complete-guide-for-workplace-safety.html)
- [Vehant - PPEye Violation Detection](https://www.vehant.com/solutions/ppeye/)
- [Pelco - PPE Detection AI-Powered](https://www.pelco.com/cameras/ppe-detection)
- [Videoloft - PPE Detection](https://videoloft.com/ppe-detection/)
- [PMC - Real-Time PPE Monitoring with On-Device AI](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991348/)

---
*Feature research for: PPE Detection / Safety Monitoring (configurable multi-class)*
*Researched: 2026-03-05*

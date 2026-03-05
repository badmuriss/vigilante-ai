# Project Research Summary

**Project:** Vigilante.AI - Multi-class PPE Detection Integration
**Domain:** Real-time computer vision / workplace safety monitoring
**Researched:** 2026-03-05
**Confidence:** HIGH

## Executive Summary

Vigilante.AI is a self-hosted, single-camera PPE monitoring system built on FastAPI + Next.js + Ultralytics YOLOv8. The current milestone requires swapping to a 6-class HuggingFace PPE model, building configurable EPI selection, implementing per-person non-accumulative infraction logic, and fixing detection instability. This is a well-understood domain -- the core challenge is not "can we detect PPE?" but rather "can we reliably track compliance state per person over time without drowning users in false alerts?"

The recommended approach is a three-phase build: (1) integrate the new model with EPI configuration and fix the stop/start bug, (2) build spatial zone tracking and the per-zone per-EPI state machine that replaces the current cooldown-based alert system, (3) polish thresholds, update dashboard stats, and add differentiator features. The critical architectural insight is that the HuggingFace model detects PPE items only -- not persons. Person-PPE association must be solved via spatial clustering of PPE detections into "zones" rather than requiring a second person-detection model, which would double inference cost and likely exceed the frame budget on CPU.

The top risks are: detection flickering causing infraction spam (mitigated by hysteresis thresholds in the state machine), class name mismatch silently breaking all detection logic when the model is swapped (mitigated by a complete rewrite of detector classification, not adaptation), and the existing stop/start crash bug making development painful (mitigated by fixing it first). Thread safety issues in shared state must also be addressed before adding the new per-zone tracking complexity.

## Key Findings

### Recommended Stack

The existing stack (FastAPI, Next.js 14, OpenCV, Ultralytics) is retained. Two new dependencies are needed, both well-maintained and battle-tested. See [STACK.md](./STACK.md) for full details.

**Core additions:**
- `huggingface_hub` (>=1.5.0): Model download and caching -- handles resume, version checking, and deterministic Docker builds via `hf_hub_download` with `local_dir`
- `supervision` (>=0.25.0): ByteTrack tracking + `DetectionsSmoother` for temporal averaging -- the smoother is the primary fix for detection flickering and is not available in Ultralytics alone
- `ultralytics` bump to >=8.3.0: Required for `supervision` compatibility; pin exact working version after verifying model loads

**Critical version note:** The HuggingFace model's training ultralytics version is unknown. Model loading must be tested first; ONNX export is the fallback if version mismatch occurs.

### Expected Features

See [FEATURES.md](./FEATURES.md) for full feature landscape and competitor analysis.

**Must have (table stakes -- this milestone):**
- 6-class model integration (foundation for everything)
- Start/stop bug fix (system stability prerequisite)
- Configurable PPE selection panel (checkboxes for 6 EPI types)
- Per-EPI violation tracking with non-accumulative infraction logic (state machine: 1 infraction if never worn, new infraction only on remove-after-wear)
- Detection smoothing/debounce (N-frame confirmation threshold)
- Portuguese-language labels across all UI surfaces

**Should have (v1.x after core is stable):**
- Per-EPI compliance breakdown in dashboard
- Per-class confidence thresholds (higher for unreliable classes like Gloves/Safety Shoes)
- Violation evidence export (CSV)
- Visual alert severity indicators

**Defer (v2+):**
- Detection zone overlay (ROI drawing tool)
- Multi-camera support
- Persistent database storage
- Per-worker identity tracking (privacy/LGPD concerns, needs face recognition)

### Architecture Approach

The architecture introduces 3 new components (PersonTracker, InfractionManager, EpiConfig) and rewrites the detection pipeline from "detect -> cooldown check -> alert" to "detect -> spatial grouping -> zone tracking -> state machine per EPI -> infraction on state transition -> alert." See [ARCHITECTURE.md](./ARCHITECTURE.md) for full component diagram and data flow.

**Major components:**
1. **EpiConfig** -- centralized EPI class definitions, active set management, Portuguese translations; replaces scattered hardcoded constants
2. **SafetyDetector (rewritten)** -- loads HF model via `huggingface_hub`, runs inference, filters by active EPIs; paradigm shift from "detect violations" to "detect presence, infer absence"
3. **PersonTracker (new)** -- spatial clustering of PPE detections into zones, centroid/IoU matching across frames, zone expiry with grace period
4. **InfractionManager (new)** -- per-zone per-EPI state machine (UNKNOWN/WEARING/MISSING) with hysteresis thresholds; replaces cooldown-based AlertManager logic
5. **AlertManager (simplified)** -- becomes pure alert storage and stats; no more deduplication logic

**Key pattern:** Asymmetric hysteresis -- require fewer frames to confirm "wearing" (3 frames) than "missing" (8 frames). It is worse to falsely accuse than to be slow to recognize compliance.

### Critical Pitfalls

See [PITFALLS.md](./PITFALLS.md) for all 11 pitfalls with detailed prevention strategies.

1. **PPE-to-person association impossible with this model alone** -- the model has no "person" class. Use spatial zone clustering instead of a second model. If zone tracking proves insufficient, fall back to dual-model pipeline but budget for the FPS hit.
2. **Detection flickering causes infraction spam** -- single-frame confidence fluctuates around threshold. Implement hysteresis with N-frame sliding window per zone per EPI. Especially critical for Gloves (0.69 mAP) and Safety Shoes (0.64 mAP).
3. **Class name mismatch silently breaks everything** -- existing code expects `no_hardhat`/`hardhat`; new model outputs `Helmet`/`Vest`/etc. with inconsistent casing. Must completely rewrite detection logic, not adapt. Remove `PPE_CLASSES`/`VIOLATION_CLASSES`/`COMPLIANT_CLASSES` entirely.
4. **Stop/start crash (known bug)** -- OpenCV VideoCapture release/reopen race condition + MJPEG generator has no cancellation. Fix with stream lifecycle state machine and delay between release/reopen.
5. **Thread safety in shared state** -- existing race conditions in AlertManager (documented in CONCERNS.md). Must fix before adding per-zone tracking state. Use `threading.RLock` consistently or restructure to single-writer pattern.

## Implications for Roadmap

Based on research, the build naturally divides into 4 phases following dependency order.

### Phase 1: Foundation -- Bug Fixes and Model Integration
**Rationale:** The stop/start bug and thread safety issues make development and testing unreliable. The model swap is the foundation for every other feature. These must come first.
**Delivers:** Stable system running the 6-class HF model with Portuguese labels, configurable EPI selection, and working stop/start lifecycle.
**Addresses:** Start/stop bug fix, thread safety fixes, 6-class model integration, EpiConfig + API endpoints, EpiConfigPanel frontend, Portuguese label mapping, updated frame annotations
**Avoids:** Pitfall 3 (stop/start crash), Pitfall 4 (class name mismatch), Pitfall 8 (thread safety), Pitfall 9 (model download in Docker), Pitfall 10 (ultralytics version mismatch)

### Phase 2: Zone Tracking and State Machine
**Rationale:** With the model working and system stable, build the core algorithmic components. Zone tracking and the infraction state machine are tightly coupled and should be built together. This is the highest-risk phase with the most novel logic.
**Delivers:** Per-zone per-EPI compliance tracking with non-accumulative infraction logic. Replaces cooldown-based alerts entirely.
**Uses:** `supervision` ByteTrack + DetectionsSmoother from STACK.md
**Implements:** PersonTracker, InfractionManager, rewired StreamProcessor pipeline
**Avoids:** Pitfall 1 (no person detection -- uses zone clustering), Pitfall 2 (flickering -- uses hysteresis), Pitfall 5 (FPS -- uses frame skipping), Pitfall 6 (tracker ID reassignment -- uses grace periods)

### Phase 3: Dashboard Enhancement and Polish
**Rationale:** Core detection and tracking are stable. Now surface the data properly in the UI and tune based on real camera testing.
**Delivers:** Per-EPI compliance breakdown, updated alert cards with zone/EPI info, tuned hysteresis thresholds, visual severity indicators.
**Addresses:** Per-EPI compliance breakdown, updated Alert model and frontend, dashboard stats enhancement, threshold tuning
**Avoids:** Pitfall 7 (state sync on config change -- implement session reset), Pitfall 11 (low-confidence classes -- add per-class thresholds and reliability indicators)

### Phase 4: Export and Hardening
**Rationale:** With a working, polished system, add compliance documentation features and production hardening.
**Delivers:** CSV violation export, per-class confidence thresholds, Docker production build with baked-in model weights.
**Addresses:** Violation evidence export, per-class confidence thresholds, Docker optimization

### Phase Ordering Rationale

- Phase 1 before Phase 2: cannot build zone tracking without the 6-class model producing real detections. Cannot develop reliably with the stop/start bug.
- Phase 2 before Phase 3: cannot show per-EPI stats in the dashboard until per-EPI tracking exists. Phase 3 is the UI layer over Phase 2's data.
- Phase 3 before Phase 4: threshold tuning and UI polish should happen with real camera testing before hardening for production.
- The dependency chain is strict: Model -> Tracking -> UI -> Export. There is no parallelism opportunity between phases.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Zone tracking via spatial clustering is the most novel component. The clustering algorithm (distance thresholds, zone matching heuristics) will need iteration during implementation. The supervision library's ByteTrack + DetectionsSmoother integration needs hands-on validation.
- **Phase 1 (partial):** The ultralytics version compatibility with the HF model weights should be validated immediately with a spike/prototype before committing to the full phase plan.

Phases with standard patterns (skip research-phase):
- **Phase 1 (model loading, API endpoints, config panel):** Well-documented patterns. HuggingFace Hub and FastAPI CRUD are straightforward.
- **Phase 3:** Standard dashboard/UI work. No novel technical challenges.
- **Phase 4:** CSV export and Docker optimization are routine.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Two well-documented libraries (huggingface_hub, supervision) with clear API examples. No exotic dependencies. |
| Features | HIGH | Competitor analysis validates feature set. Clear table-stakes vs differentiator separation. MVP scope is well-bounded. |
| Architecture | HIGH | State machine and zone tracking patterns are well-understood. The critical insight (no person class in model) was caught early. |
| Pitfalls | HIGH | 11 pitfalls identified with concrete prevention strategies. Top risks (flickering, class mismatch, stop/start bug) have clear solutions. |

**Overall confidence:** HIGH

### Gaps to Address

- **Zone clustering accuracy:** The spatial clustering approach for person-PPE association has not been validated with real camera footage. If workers stand close together, zone boundaries may overlap. Validate early in Phase 2 with real test footage; have the dual-model fallback plan ready.
- **Ultralytics version compatibility:** The exact ultralytics version that trained the HF model is unknown. Run a model loading spike at the start of Phase 1 to confirm compatibility before writing detection logic.
- **Hysteresis threshold values:** The recommended CONFIRM_WEARING=3 and CONFIRM_MISSING=8 are educated guesses. Real values need tuning with actual camera and environment conditions during Phase 3.
- **Model performance in target environment:** The model's mAP metrics are from its training/validation set. Real-world accuracy with the target webcam, lighting, and angles is unknown. Plan for threshold adjustment.

## Sources

### Primary (HIGH confidence)
- [Tanishjain9/yolov8n-ppe-detection-6classes](https://huggingface.co/Tanishjain9/yolov8n-ppe-detection-6classes) -- model classes, mAP, architecture
- [HuggingFace Hub download docs](https://huggingface.co/docs/huggingface_hub/en/guides/download) -- hf_hub_download API
- [Supervision DetectionsSmoother](https://supervision.roboflow.com/latest/detection/tools/smoother/) -- smoother API, sliding window behavior
- [Ultralytics YOLO tracking docs](https://docs.ultralytics.com/modes/track/) -- ByteTrack/BoTSORT configuration
- Project codebase analysis (detector.py, stream.py, alerts.py, camera.py, CONCERNS.md)

### Secondary (MEDIUM confidence)
- [Protex AI](https://www.protex.ai/product/ppe-detection), [Visionify](https://visionify.ai/ppe-compliance), [viAct.ai](https://www.viact.ai/ppedetection) -- competitor feature analysis
- [PMC - Real-Time PPE Monitoring](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991348/) -- temporal smoothing approaches
- Ultralytics GitHub issues (#17870, #15609, #13902) -- version compatibility, performance optimization

### Tertiary (LOW confidence)
- Hysteresis threshold recommendations (3/8 frames) -- educated estimates, need real-world validation
- Zone clustering distance thresholds -- untested, need empirical tuning

---
*Research completed: 2026-03-05*
*Ready for roadmap: yes*

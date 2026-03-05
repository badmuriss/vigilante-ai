# Domain Pitfalls

**Domain:** Real-time PPE detection with per-person tracking and configurable monitoring
**Researched:** 2026-03-05

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: PPE-to-Person Association Without a Person Detector

**What goes wrong:** The HuggingFace model (`Tanishjain9/yolov8n-ppe-detection-6classes`) detects 6 PPE classes (Gloves, Vest, Goggles, Helmet, Mask, Safety Shoe) but does NOT detect "person" as a class. The current codebase has no mechanism to associate which PPE belongs to which person. Without person detection, you cannot determine "Person A is missing a helmet" -- you only know "there is a helmet somewhere in frame." This is fundamentally incompatible with the requirement for per-person infraction tracking ("nova infracao cada vez que a pessoa coloca EPI e depois tira").

**Why it happens:** The PPE model only outputs equipment bounding boxes, not person bounding boxes. Developers assume "detect PPE" is the same as "detect PPE compliance per person" -- it is not.

**Consequences:** Without person association: (1) impossible to track individual compliance states, (2) impossible to say "person X removed their helmet," (3) the entire per-person infraction logic cannot work, (4) a helmet on a shelf registers as compliance. This would require a fundamental architecture rewrite later.

**Prevention:**
- Run two models or a two-stage pipeline: first detect persons (use the standard `yolov8n.pt` COCO model which detects "person" class), then check which PPE bounding boxes overlap with each person's bounding box using spatial containment/IoU.
- Alternatively, use Ultralytics built-in tracking (`model.track()`) with ByteTrack or BoTSORT to get persistent person IDs, then spatially match PPE detections to tracked persons.
- The spatial matching logic: for each person bbox, check which PPE bboxes have their center point inside the person bbox, or have IoU > threshold with relevant body regions.

**Detection (warning signs):**
- You find yourself writing infraction logic that only knows "helmet detected: yes/no" globally rather than per-person.
- Your alert says "no helmet" but there are 3 people in frame and only 1 is missing a helmet.

**Phase:** Must be addressed in the first phase (model integration). This is architectural -- retrofitting it later means rewriting all detection and alert logic.

**Confidence:** HIGH -- verified by inspecting the HuggingFace model's 6 classes (none is "person") and the current codebase requirements.

---

### Pitfall 2: Detection Flickering Causes Infraction Spam

**What goes wrong:** YOLOv8 detection confidence fluctuates frame-to-frame. A helmet detection might be 0.52 on frame N, 0.48 on frame N+1 (below threshold), and 0.53 on frame N+2. This causes rapid on/off toggling ("flickering"). With the new infraction logic ("nova infracao cada vez que a pessoa coloca EPI e depois tira"), every flicker cycle generates a false infraction. The current codebase has a cooldown timer (`ALERT_COOLDOWN_SECONDS = 10`) but the new requirement explicitly asks for per-event tracking -- cooldown alone will not solve this.

**Why it happens:** Single-frame detection is inherently noisy. Confidence scores hover near the threshold. Partial occlusions, motion blur, lighting changes, and camera angle all cause momentary detection drops. The PPE model has lower mAP for Gloves (~0.69) and Safety Shoes (~0.64), making these classes especially flicker-prone.

**Consequences:** (1) Hundreds of false infractions in minutes, (2) users lose trust in the system, (3) compliance rate becomes meaningless, (4) the "put on then removed" logic fires constantly on phantom events.

**Prevention:**
- Implement temporal smoothing: maintain a sliding window of N frames (e.g., 5-10 frames) per person per PPE class. Only transition state (wearing -> not wearing) when the detection is consistently absent for K consecutive frames.
- Use hysteresis thresholds: require confidence > 0.6 to transition to "wearing" but only drop to "not wearing" when confidence < 0.3 for several frames. This prevents oscillation around a single threshold.
- Apply Kalman filter or exponential moving average on detection confidence per tracked object.
- The frame window size should be configurable -- too short and flickering persists, too long and real removals are delayed.

**Detection (warning signs):**
- During testing, infraction count climbs rapidly even when nobody moves.
- Compliance rate swings wildly second-to-second.
- Alert log shows rapid alternating "detected/not detected" entries for the same PPE type.

**Phase:** Must be addressed alongside per-person tracking (same phase as model integration). The temporal smoothing state lives on the per-person tracker, so these are tightly coupled.

**Confidence:** HIGH -- this is the most commonly reported issue in real-time PPE detection systems, confirmed by multiple sources and visible in the current codebase's alert behavior.

---

### Pitfall 3: Stop/Start Stream Crashes Due to Thread and Camera Lifecycle Bugs

**What goes wrong:** The current `StreamProcessor.stop()` sets `_running = False`, joins the processing thread, then calls `camera.stop()`. But `generate_mjpeg()` runs in a separate context (the MJPEG streaming response) and checks `self._running` -- if a client is still connected when stop is called, the generator continues running. On restart, `start()` creates a new thread while the old MJPEG generator may still be referencing stale state. Additionally, `cv2.VideoCapture.release()` followed by a new `cv2.VideoCapture()` on the same camera index can fail silently or hang on some platforms (Linux V4L2, macOS AVFoundation) if the release has not fully completed.

**Why it happens:** OpenCV's VideoCapture is not thread-safe. The camera device (e.g., `/dev/video0`) is an OS-level resource that may not be immediately available after release. The MJPEG generator has no connection cleanup or cancellation mechanism. The `_running` flag is checked without synchronization in multiple threads.

**Consequences:** (1) System hangs on restart -- the known bug in PROJECT.md ("ao parar e iniciar a deteccao, o sistema trava"), (2) camera resource leak (webcam light stays on), (3) stale frames served to connected clients, (4) potential segfault in OpenCV if two threads access VideoCapture simultaneously.

**Prevention:**
- Add a short delay (200-500ms) between `camera.stop()` and `camera.start()` to let the OS release the device.
- Track active MJPEG generator connections and cancel them on stop (use `asyncio.Event` or a cancellation token).
- Use FastAPI lifespan events for proper cleanup on shutdown.
- Verify camera is actually released before attempting reopen: retry `cv2.VideoCapture.open()` with a timeout.
- Consider using `asyncio` generators for MJPEG instead of synchronous generators with `time.sleep()` -- this enables proper cancellation.
- Add a state machine for stream lifecycle: `STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED` with transitions guarded by a lock.

**Detection (warning signs):**
- Webcam LED stays on after clicking "stop."
- Second "start" click returns success but no video frames appear.
- Backend logs show "Camera started" but `get_frame()` returns None.
- Process CPU usage remains high after stop.

**Phase:** Should be fixed before adding new detection features. A broken start/stop cycle makes all development and testing painful. Address in the first phase or as a prerequisite.

**Confidence:** HIGH -- the bug is already documented in PROJECT.md and the root causes are visible in the code (`generate_mjpeg` has no cancellation, no delay between release/reopen).

---

### Pitfall 4: HuggingFace Model Class Mismatch With Existing Detection Logic

**What goes wrong:** The current `SafetyDetector` expects PPE classes like `hardhat`, `no_hardhat`, `safety_glasses`, `no_safety_glasses` (defined in `PPE_CLASSES`, `VIOLATION_CLASSES`, `COMPLIANT_CLASSES`). The HuggingFace model outputs completely different class names: `Gloves`, `Vest`, `Goggles`, `Helmet`, `Mask`, `Safety Shoe` (note: capitalized, different naming convention, and NO "no_X" violation classes). The model only detects presence of PPE -- it does not have "no_helmet" as a class. Violations must be inferred by absence.

**Why it happens:** The existing code was written for a different model architecture that had explicit violation classes (`no_hardhat`). The new model follows a different paradigm: detect what IS present, then infer violations by what is NOT present on a tracked person.

**Consequences:** If you simply swap the model path without rewriting the detection logic: (1) `PPE_CLASSES` intersection check will find zero matches (different names), (2) the fallback "person" logic kicks in and every person is flagged as `no_hardhat`, (3) all 6 PPE classes are silently ignored, (4) the system appears to work but produces entirely wrong results.

**Prevention:**
- Completely rewrite the detection classification logic. The new paradigm is: detect all PPE present -> associate with persons -> for each person, check which of the configured EPIs are NOT detected -> those are violations.
- Create a mapping layer: `{"Helmet": "capacete", "Vest": "colete", ...}` for both internal logic and Portuguese display names.
- Remove the `PPE_CLASSES` / `VIOLATION_CLASSES` / `COMPLIANT_CLASSES` constants entirely -- they encode the wrong model paradigm.
- Write integration tests that load the actual HuggingFace model and verify class name extraction works before building detection logic on top.

**Detection (warning signs):**
- `_has_ppe_classes` is `False` after loading the new model.
- Log message says "Model does not have PPE classes. Using person detection as fallback."
- All detections show as `no_hardhat` regardless of what the camera sees.

**Phase:** First phase -- this is the model integration step. Must be done before any infraction logic changes.

**Confidence:** HIGH -- verified by comparing the model's actual class names (from HuggingFace model card) against the hardcoded constants in `detector.py`.

---

## Moderate Pitfalls

### Pitfall 5: Running YOLO Inference on Every Frame Kills FPS With Added Complexity

**What goes wrong:** The current pipeline runs YOLO inference on every frame (`_process_loop` in `stream.py`). Adding per-person tracking (e.g., `model.track()` with ByteTrack) increases per-frame cost. Adding a second model pass for person detection doubles it. With the PPE model (yolov8n at 640x640) on CPU, expect ~30-80ms per inference. Two passes = 60-160ms per frame = 6-16 FPS at best, dropping below the 15 FPS requirement.

**Prevention:**
- Implement frame skipping: run full inference every Nth frame (e.g., every 3rd), reuse the last detection results for intermediate frames.
- Use Ultralytics' built-in `model.track(persist=True)` which handles tracking state between frames -- this is more efficient than running detection + separate tracker.
- Consider a single combined model approach: detect persons AND PPE in one pass. If infeasible with the current model, use the PPE model's output and run person detection only every Kth frame (persons move slowly, PPE changes rarely).
- Export the model to ONNX or TensorRT for 2-5x inference speedup.
- Separate the capture thread (runs at camera FPS) from the inference thread (runs as fast as it can) -- the current architecture already does this partially but the processing loop has no skip logic.

**Detection (warning signs):**
- FPS counter drops below 10 after adding tracking.
- Visible lag between real movement and on-screen annotation.
- CPU usage pegged at 100% on all cores.

**Phase:** Address during model integration phase. Frame skipping and performance budgeting should be designed alongside the dual-model pipeline, not bolted on after.

**Confidence:** HIGH -- yolov8n inference times are well-documented; two model passes on CPU will exceed frame budget.

---

### Pitfall 6: Tracker ID Reassignment Creates Phantom Infractions

**What goes wrong:** Object trackers (ByteTrack, BoTSORT) assign IDs to tracked persons. When a person is temporarily occluded (walks behind another, turns away), the tracker loses them and assigns a NEW ID when they reappear. The per-person state (which PPE they were wearing, infraction history) is tied to the old ID and effectively lost. The "new" person starts with a clean slate, potentially triggering false "never wore PPE" infractions.

**Why it happens:** Re-identification (ReID) in BoTSORT helps but is not perfect. ByteTrack has no ReID at all. Webcam-quality video at 640x480 provides limited appearance features for matching. People in similar uniforms/PPE look nearly identical to the tracker.

**Prevention:**
- Use BoTSORT over ByteTrack -- it includes ReID features that reduce ID reassignment.
- Tune tracker parameters: increase `track_buffer` (frames to keep lost tracks alive) in the tracker YAML config. Default is often 30 frames; for a workplace monitoring scenario where people might be briefly occluded, increase to 60-90.
- Design infraction logic to be forgiving of ID changes: new IDs start with a grace period before infractions are counted.
- Accept that perfect tracking is impossible -- design the UX to show "approximate" per-person stats rather than promising exact per-person audit trails.
- Consider zone-based monitoring as a fallback: "in this zone, PPE compliance is X%" rather than strictly per-person.

**Detection (warning signs):**
- Person count fluctuates when nobody enters or leaves the frame.
- Infraction count spikes when people walk past each other.
- The same physical person shows up with multiple IDs in the tracking log.

**Phase:** Address during per-person tracking implementation. Tracker configuration and infraction grace periods are part of the same work.

**Confidence:** MEDIUM -- based on documented tracker behavior from Ultralytics discussions; severity depends on the specific deployment environment.

---

### Pitfall 7: Configurable EPI Selection Creates State Synchronization Bugs

**What goes wrong:** The frontend sends a list of active EPIs (e.g., `["Helmet", "Vest"]`). The backend must filter infractions to only the selected EPIs. But: (1) if the list changes mid-stream, existing per-person tracking state may reference EPIs that are no longer monitored, (2) compliance rate calculation becomes invalid if the denominator changes, (3) alerts already generated for a now-deselected EPI remain in the alert list, confusing users.

**Prevention:**
- When the EPI configuration changes: reset per-person tracking state, clear the compliance rate counters, but keep existing alerts (mark them with the config that was active when they were generated).
- The backend should validate the EPI list against known model classes and reject unknown values.
- Store the active EPI config as part of the "session" concept -- changing EPIs effectively starts a new monitoring session.
- Use an API endpoint (e.g., `PUT /api/config/epis`) that returns the new session state, so the frontend knows to refresh stats.

**Detection (warning signs):**
- Compliance rate jumps to 100% after deselecting an EPI that was causing violations.
- Old alerts reference EPIs that are no longer in the active list.
- Per-person state shows "missing Helmet" infraction when Helmet monitoring is off.

**Phase:** Address during the configurable monitoring phase, after per-person tracking is stable.

**Confidence:** MEDIUM -- this is an application-logic concern specific to this project's requirements.

---

### Pitfall 8: Thread Safety Race Conditions in AlertManager and StreamProcessor

**What goes wrong:** The CONCERNS.md already documents this: `_is_on_cooldown()` reads `self._cooldowns` without a lock, `record_frame()` modifies counters without a lock, `get_stats()` reads shared state without a lock. Adding per-person tracking state (dictionaries of person ID -> PPE state) to this already-unsafe architecture will multiply race condition surface area. Symptoms include corrupted infraction counts, missed alerts, and occasional crashes.

**Prevention:**
- Before adding any new state, fix the existing thread safety issues: use `threading.RLock` consistently for ALL reads and writes to shared state.
- Consider restructuring to use a single processing thread that owns all mutable state, with the API thread reading via thread-safe snapshots (copy-on-read).
- For per-person state, use a dedicated `PersonTracker` class with its own lock, rather than adding more dictionaries to `AlertManager`.
- Write concurrent stress tests (use `concurrent.futures.ThreadPoolExecutor`) to validate thread safety before adding complexity.

**Detection (warning signs):**
- Intermittent `KeyError` or `RuntimeError: dictionary changed size during iteration`.
- Alert counts don't match between `/api/alerts` and `/api/stats`.
- Compliance rate occasionally shows impossible values (> 100% or negative).

**Phase:** Fix as a prerequisite in the first phase, before adding per-person tracking state.

**Confidence:** HIGH -- race conditions are already documented in CONCERNS.md and visible in the code.

---

## Minor Pitfalls

### Pitfall 9: HuggingFace Model Download Fails in Docker/CI

**What goes wrong:** Loading a model from HuggingFace (`YOLO("Tanishjain9/yolov8n-ppe-detection-6classes")`) requires internet access and HuggingFace Hub authentication for some models. Docker builds in isolated networks or CI pipelines may fail silently or hang waiting for the download.

**Prevention:**
- Download the model weights (`.pt` file) during Docker build or as a setup step, not at runtime.
- Store the weights file in a known location and load via local path: `YOLO("/app/models/ppe-6classes.pt")`.
- Add the model download to a `Makefile` or setup script: `huggingface-cli download Tanishjain9/yolov8n-ppe-detection-6classes --local-dir ./models/`.
- Add a health check that verifies the model file exists before accepting traffic.

**Phase:** Address during model integration (first phase).

**Confidence:** MEDIUM -- depends on how the model is distributed (direct .pt download vs HF Hub API).

---

### Pitfall 10: Ultralytics Version Incompatibility With Pre-trained Weights

**What goes wrong:** Ultralytics updates frequently and occasionally changes the model serialization format or internal architecture. A `.pt` file saved with ultralytics 8.0.x may fail to load with ultralytics 8.2.x with cryptic errors like "Loading mismatched weights" or architecture mismatch. The HuggingFace model card does not specify which ultralytics version was used for training.

**Prevention:**
- Pin the `ultralytics` version in `requirements.txt` to the exact version that successfully loads the model.
- Test model loading as the FIRST step of integration, before writing any detection logic.
- If version mismatch occurs, export the model to ONNX format (which is version-independent) and use ONNX Runtime for inference.
- Document the working ultralytics version in the project README/config.

**Phase:** Address immediately during model integration.

**Confidence:** MEDIUM -- based on multiple GitHub issues about weight loading failures across versions.

---

### Pitfall 11: Low-Confidence PPE Classes (Gloves, Safety Shoes) Generate Excessive False Alerts

**What goes wrong:** The model's mAP for Gloves (~0.69) and Safety Shoes (~0.64) is significantly lower than Helmet (~0.90) or Vest (~0.90). At the default confidence threshold of 0.5, these classes will produce many false positives and false negatives. Users who enable Gloves or Safety Shoes monitoring will see unreliable results and lose trust in the system.

**Prevention:**
- Use per-class confidence thresholds rather than a single global threshold. Set higher thresholds for unreliable classes (e.g., 0.6 for Gloves, 0.65 for Safety Shoes).
- In the UI configuration panel, show a reliability indicator next to each EPI class (e.g., "Alta confiabilidade" vs "Confiabilidade moderada").
- Consider recommending against enabling low-confidence classes in production until results are validated.
- The temporal smoothing from Pitfall 2 helps here too -- requiring sustained detection reduces false positive impact.

**Phase:** Address during configurable monitoring implementation.

**Confidence:** HIGH -- mAP values are from the model card; lower mAP directly correlates with more detection errors.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Model integration (HF model swap) | Class name mismatch breaks all detection logic (Pitfall 4) | Rewrite detector from scratch for new paradigm; do not try to adapt existing code |
| Model integration (HF model swap) | Model download fails in Docker (Pitfall 9) | Download weights at build time, load from local path |
| Model integration (HF model swap) | Ultralytics version mismatch (Pitfall 10) | Pin version, test loading first |
| Per-person tracking | No person detection in PPE model (Pitfall 1) | Two-model pipeline or use model.track() for person association |
| Per-person tracking | Tracker ID reassignment (Pitfall 6) | Use BoTSORT, increase track_buffer, add grace periods |
| Per-person tracking | Thread safety in shared state (Pitfall 8) | Fix locks before adding complexity |
| Detection stabilization | Flickering causes infraction spam (Pitfall 2) | Temporal smoothing with sliding window per person per class |
| Detection stabilization | Low-confidence classes unreliable (Pitfall 11) | Per-class thresholds, reliability indicators |
| Configurable monitoring | State sync bugs on config change (Pitfall 7) | Reset session on config change, validate input |
| Stop/start stream | Camera lifecycle crash (Pitfall 3) | State machine, delay between release/reopen, MJPEG cancellation |
| Performance | Dual-model pipeline exceeds frame budget (Pitfall 5) | Frame skipping, ONNX export, inference throttling |

## Sources

- [Ultralytics Multi-Object Tracking Docs](https://docs.ultralytics.com/modes/track/) -- ByteTrack/BoTSORT configuration, `model.track()` API
- [Tanishjain9/yolov8n-ppe-detection-6classes on HuggingFace](https://huggingface.co/Tanishjain9/yolov8n-ppe-detection-6classes) -- model classes, mAP values, limitations
- [Ultralytics GitHub Issue #17870: Loading mismatched weights](https://github.com/ultralytics/ultralytics/issues/17870) -- version compatibility issues
- [Ultralytics GitHub Issue #15609: Problem Loading Custom Pretrained Weights](https://github.com/ultralytics/ultralytics/issues/15609) -- HF model loading
- [OpenCV GitHub Issue #12301: Webcam light still on after cam.release()](https://github.com/opencv/opencv/issues/12301) -- camera release bugs
- [OpenCV GitHub Issue #12763: OpenCV crash when open webcam](https://github.com/opencv/opencv/issues/12763) -- VideoCapture thread safety
- [OpenCV Q&A: Decrease flickering effect of bounding box](https://answers.opencv.org/question/180174/how-to-decrease-flickering-effect-of-bounding-box-in-object-detection-by-cascade-classifier/) -- temporal smoothing approaches
- [Ultralytics GitHub Discussion #19784: ID Reassignment in BoT-SORT and ByteTrack](https://github.com/orgs/ultralytics/discussions/19784) -- tracker ID instability
- [PPE Detection Using YOLOv8 Comparative Study](https://www.tandfonline.com/doi/full/10.1080/23311916.2024.2333209) -- PPE detection accuracy limitations
- [Ultralytics GitHub Issue #13902: How to increase inference speed](https://github.com/ultralytics/ultralytics/issues/13902) -- performance optimization
- Project codebase: `backend/app/detector.py`, `backend/app/stream.py`, `backend/app/alerts.py`, `backend/app/camera.py`, `backend/app/main.py`
- `.planning/codebase/CONCERNS.md` -- existing thread safety and architecture issues

---

*Concerns audit: 2026-03-05*

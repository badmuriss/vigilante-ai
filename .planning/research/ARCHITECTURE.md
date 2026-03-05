# Architecture Patterns

**Domain:** Configurable multi-class PPE detection with per-person state tracking
**Researched:** 2026-03-05

## Critical Design Constraint

The HuggingFace model `Tanishjain9/yolov8n-ppe-detection-6classes` detects **PPE items only** -- it does NOT detect persons. Its 6 classes are: `Gloves`, `Vest`, `goggles`, `helmet`, `mask`, `safety_shoe`. This means the system cannot directly associate "person X is missing helmet" from this model alone.

**Implication:** Without person detection, the system cannot do true per-person tracking with this model. The architecture must work within this constraint. Two viable approaches exist (see "Person-PPE Association Strategy" below).

## Recommended Architecture

### High-Level Component Diagram

```
Frontend (Next.js)                     Backend (FastAPI)
+---------------------------+          +------------------------------------------+
| MonitoringPage            |          | API Layer (main.py)                      |
|  +-- VideoFeed            |  MJPEG   |  GET /api/stream                         |
|  +-- EpiConfigPanel [NEW] | -------> |  GET/PUT /api/config/epi  [NEW]          |
|  +-- AlertPanel           |  REST    |  GET /api/alerts                         |
|  +-- Controls             | <------> |  GET /api/stats                          |
+---------------------------+          +------------------------------------------+
                                       | StreamProcessor (stream.py)              |
                                       |  orchestrates pipeline                   |
                                       +------------------------------------------+
                                       | SafetyDetector (detector.py)             |
                                       |  YOLO inference + PPE class mapping      |
                                       +------------------------------------------+
                                       | PersonTracker [NEW] (tracker.py)         |
                                       |  spatial PPE-to-zone association          |
                                       |  per-zone state machine                  |
                                       +------------------------------------------+
                                       | InfractionManager [NEW] (infractions.py) |
                                       |  state-based violation logic             |
                                       |  replaces simple cooldown approach       |
                                       +------------------------------------------+
                                       | AlertManager (alerts.py)                 |
                                       |  alert storage + stats (mostly unchanged)|
                                       +------------------------------------------+
                                       | EpiConfig [NEW] (epi_config.py)          |
                                       |  active EPI set management               |
                                       +------------------------------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `EpiConfig` | Holds the set of active EPI types; provides translation map (EN->PT) | Read by `InfractionManager`, `SafetyDetector`, API layer |
| `SafetyDetector` | YOLO inference; filters detections to only active EPIs | Read from `EpiConfig`; outputs `Detection` list to `StreamProcessor` |
| `PersonTracker` | Groups PPE detections into spatial zones; maintains zone identity across frames | Receives `Detection` list; outputs `TrackedZone` list with associated EPIs |
| `InfractionManager` | Per-zone per-EPI state machine; decides when to emit infractions | Receives `TrackedZone` list + active EPI set; emits `Infraction` events to `AlertManager` |
| `AlertManager` | Stores alerts, computes stats (mostly unchanged) | Receives infractions; serves API layer |
| `StreamProcessor` | Orchestrates the pipeline per frame | Coordinates all components |
| `EpiConfigPanel` (frontend) | Checkboxes for 6 EPI types | Calls `PUT /api/config/epi` |

## Person-PPE Association Strategy

Since the model detects PPE items but not persons, we need a strategy for "who is wearing what."

### Recommended: Spatial Zone Tracking (no person detection needed)

**Concept:** Use the spatial clustering of PPE detections to infer "zones" where a person likely is. A cluster of helmet + vest + goggles in the same area = one person. Track these zones across frames using simple centroid/IoU tracking.

**Why this works for the use case:**
- The camera is typically fixed (security/workplace camera)
- Workers occupy distinct spatial zones in most industrial settings
- We don't need to identify WHO the person is, just track that "zone A was compliant, then became non-compliant"

**Implementation:**

```python
@dataclass
class TrackedZone:
    zone_id: int
    centroid: tuple[float, float]  # center of the PPE cluster
    bbox: tuple[int, int, int, int]  # bounding region of all EPIs in this zone
    detected_epis: set[str]  # e.g. {"helmet", "Vest"}
    frames_seen: int
    last_seen_frame: int
```

**Zone association algorithm (per frame):**
1. Run YOLO inference -> get all PPE detections
2. Cluster nearby detections using simple distance threshold (e.g., if two detections overlap or are within N pixels vertically, they belong to the same zone)
3. Match new clusters to existing zones using centroid distance (IoU or Euclidean)
4. If a cluster matches an existing zone -> update it
5. If no match -> create new zone
6. If existing zone has no match for K frames -> expire it

**Why NOT use a second person-detection model:**
- Adds latency (two model inferences per frame)
- The YOLOv8n generic model's "person" class is not reliable enough (mentioned as a current false-positive source)
- Zone tracking achieves the same goal for fixed-camera scenarios without the cost

### Alternative: Dual-Model (person detection + PPE detection)

Use `yolov8n.pt` for person bounding boxes, then check which PPE detections fall within each person box. This is more accurate but doubles inference time. **Only consider this if zone tracking proves insufficient in testing.**

## Per-Zone Per-EPI State Machine

This is the core logic that replaces the current cooldown-based approach.

### States (per zone, per EPI type)

```
                    EPI detected
    +----------+  for N frames   +-----------+
    |          | --------------> |           |
    | MISSING  |                 |  WEARING  |
    |          | <-------------- |           |
    +----------+  EPI absent     +-----------+
         |        for M frames        |
         |                            |
         v                            v
  (emit infraction              (emit infraction
   on entry, ONCE)               on transition
                                 WEARING -> MISSING)
```

### State Definitions

```python
from enum import Enum

class EpiState(Enum):
    UNKNOWN = "unknown"      # Initial state, no data yet
    WEARING = "wearing"      # EPI consistently detected
    MISSING = "missing"      # EPI consistently absent

@dataclass
class EpiStateEntry:
    state: EpiState = EpiState.UNKNOWN
    consecutive_detected: int = 0    # frames with EPI detected
    consecutive_absent: int = 0      # frames without EPI detected
    infraction_emitted: bool = False  # for MISSING state: already counted?
    last_transition_time: datetime | None = None
```

### Transition Logic

```python
CONFIRM_FRAMES = 5  # frames needed to confirm a state change

def update_epi_state(entry: EpiStateEntry, epi_detected: bool) -> Infraction | None:
    """Returns an Infraction if a new violation should be recorded."""
    infraction = None

    if epi_detected:
        entry.consecutive_detected += 1
        entry.consecutive_absent = 0
    else:
        entry.consecutive_absent += 1
        entry.consecutive_detected = 0

    if entry.state == EpiState.UNKNOWN:
        if entry.consecutive_detected >= CONFIRM_FRAMES:
            entry.state = EpiState.WEARING
            entry.infraction_emitted = False
        elif entry.consecutive_absent >= CONFIRM_FRAMES:
            entry.state = EpiState.MISSING
            # First time seen without EPI -> 1 infraction
            entry.infraction_emitted = True
            infraction = Infraction(reason="never_worn")

    elif entry.state == EpiState.WEARING:
        if entry.consecutive_absent >= CONFIRM_FRAMES:
            entry.state = EpiState.MISSING
            entry.infraction_emitted = True
            entry.last_transition_time = datetime.now()
            # Was wearing, took it off -> new infraction
            infraction = Infraction(reason="removed")

    elif entry.state == EpiState.MISSING:
        if entry.consecutive_detected >= CONFIRM_FRAMES:
            entry.state = EpiState.WEARING
            entry.infraction_emitted = False
            # Put it back on -> reset, ready for next removal
        # If still MISSING and infraction already emitted -> no duplicate

    return infraction
```

### Why This Solves the Requirements

| Requirement | How State Machine Handles It |
|-------------|------------------------------|
| "Only 1 infraction if never wore EPI" | `UNKNOWN -> MISSING` emits once, `infraction_emitted` flag prevents repeats |
| "New infraction each time EPI removed after wearing" | `WEARING -> MISSING` always emits |
| "No flickering/instability" | `CONFIRM_FRAMES` threshold prevents single-frame noise from causing transitions |
| "Independent per EPI type" | Each zone has a `dict[str, EpiStateEntry]` -- one entry per active EPI |
| "Separate alerts for each missing EPI" | Each EPI type transitions independently, emits its own infraction |

## Configurable EPI Selection -- API Design

### New Endpoints

```
GET  /api/config/epi   -> { "available": [...], "active": [...] }
PUT  /api/config/epi   <- { "active": ["helmet", "Vest", "goggles"] }
```

### Backend Data Model

```python
# epi_config.py

EPI_CLASSES: dict[str, str] = {
    "Gloves": "Luvas",
    "Vest": "Colete",
    "goggles": "Protecao ocular",
    "helmet": "Capacete",
    "mask": "Mascara",
    "safety_shoe": "Calcado de seguranca",
}

class EpiConfig:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # All active by default
        self._active: set[str] = set(EPI_CLASSES.keys())

    @property
    def available(self) -> list[dict[str, str]]:
        return [{"id": k, "label_pt": v} for k, v in EPI_CLASSES.items()]

    @property
    def active(self) -> set[str]:
        with self._lock:
            return set(self._active)

    def set_active(self, epi_ids: list[str]) -> None:
        valid = {eid for eid in epi_ids if eid in EPI_CLASSES}
        with self._lock:
            self._active = valid
```

### Pydantic Schemas

```python
class EpiOption(BaseModel):
    id: str
    label_pt: str

class EpiConfigResponse(BaseModel):
    available: list[EpiOption]
    active: list[str]

class EpiConfigUpdate(BaseModel):
    active: list[str]
```

### Frontend Integration

```typescript
// types/index.ts additions
interface EpiOption {
  id: string;
  label_pt: string;
}

interface EpiConfigResponse {
  available: EpiOption[];
  active: string[];
}
```

The `EpiConfigPanel` component renders checkboxes for each available EPI with its Portuguese label. On change, it PUTs the new active list. The backend immediately adjusts which EPIs generate infractions (detections for non-active EPIs are still drawn on the frame but do not trigger state machine evaluation).

## Data Flow for Violation Detection (New Pipeline)

```
Frame from CameraManager
    |
    v
SafetyDetector.detect(frame)
    |  Returns: list[Detection] for all 6 classes
    v
Filter by EpiConfig.active
    |  Only active EPIs proceed to tracking
    v
PersonTracker.update(detections, frame_number)
    |  1. Cluster detections spatially
    |  2. Match clusters to existing zones
    |  3. Return list[TrackedZone] with detected_epis per zone
    v
InfractionManager.evaluate(tracked_zones, active_epis)
    |  For each zone, for each active EPI:
    |    - Is this EPI in zone.detected_epis?
    |    - Update state machine for (zone_id, epi_type)
    |    - If state transition emits infraction -> collect it
    |  Returns: list[Infraction]
    v
AlertManager.add_alert() for each infraction
    |  Store with zone_id, epi_type, reason, thumbnail
    v
SafetyDetector.annotate_frame(frame, detections, tracked_zones)
    |  Draw bounding boxes with zone IDs
    |  Color-code: green=compliant, red=missing active EPI
    v
JPEG encode -> MJPEG stream
```

### Key Difference from Current Architecture

**Current:** `detection -> is it a violation class? -> cooldown check -> alert`
**New:** `detection -> spatial grouping -> zone tracking -> state machine per EPI -> infraction on state transition -> alert`

The cooldown-based approach in `AlertManager` is replaced by the state machine in `InfractionManager`. The `AlertManager` becomes a pure storage/stats layer.

## Updated Domain Models

```python
# models.py additions

@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]

@dataclass
class TrackedZone:
    zone_id: int
    centroid: tuple[float, float]
    bbox: tuple[int, int, int, int]
    detected_epis: set[str]

@dataclass
class Infraction:
    zone_id: int
    epi_type: str
    reason: str  # "never_worn" | "removed"
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Alert:
    violation_type: str       # EPI type in Portuguese
    epi_id: str               # Original EPI class name
    zone_id: int              # Which tracked zone
    reason: str               # "never_worn" | "removed"
    confidence: float
    frame_thumbnail: str
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
```

## Patterns to Follow

### Pattern 1: Hysteresis Thresholding for Detection Stability

**What:** Require N consecutive frames to confirm a state change (both directions).
**When:** Any time detection results are used to make a binary decision.
**Why:** Single-frame detection is noisy. The model will occasionally miss an EPI that is clearly there (especially `Gloves` at 0.69 mAP and `safety_shoe` at 0.64 mAP). Without hysteresis, the system "flickers" between states.

**Recommended values:**
- `CONFIRM_WEARING = 3` frames (faster to acknowledge compliance)
- `CONFIRM_MISSING = 8` frames (slower to trigger violation -- reduces false alarms)

Asymmetric thresholds are intentional: it is worse to falsely accuse someone of not wearing PPE than to be slow to recognize they put it on.

### Pattern 2: Configuration as Runtime State (Not Restart)

**What:** EPI configuration changes take effect immediately without restarting the stream.
**When:** User toggles EPI checkboxes.
**Why:** The `EpiConfig` is read every frame cycle. Changing the active set just means the next frame evaluation skips/includes different EPIs. No need to restart the detection pipeline.

**Important:** When an EPI is deactivated, clear its state machine entries for all zones. When reactivated, zones start fresh in `UNKNOWN` state.

### Pattern 3: Zone Expiry with Grace Period

**What:** When a zone (person) leaves the frame, keep its state for T seconds before expiring.
**When:** A tracked zone has no matching detections.
**Why:** A person may be momentarily occluded or step out of frame briefly. Without a grace period, they would be treated as a new zone when they return, losing their state history.

**Recommended:** 30 frames (~2 seconds at 15 FPS) grace period before zone expiry.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Global Violation State

**What:** Treating the entire frame as "compliant" or "non-compliant" without per-zone granularity.
**Why bad:** If two workers are in frame, one compliant and one not, the system cannot distinguish them. This is the current architecture's approach (`record_frame(compliant=is_compliant)`).
**Instead:** Track compliance per zone. Overall compliance = (compliant zone-frames / total zone-frames).

### Anti-Pattern 2: Cooldown-Based Deduplication

**What:** Using time-based cooldowns to prevent duplicate alerts (current `AlertManager` approach).
**Why bad:** A cooldown of 10 seconds means if someone removes their helmet, gets an alert, puts it back on, and removes it again within 10 seconds -- the second removal is silently ignored. The state machine approach is strictly superior: it emits exactly when a `WEARING -> MISSING` transition occurs, regardless of timing.
**Instead:** Use the state machine. Remove the cooldown logic entirely.

### Anti-Pattern 3: Hardcoded Class Names Throughout Codebase

**What:** Scattering `"helmet"`, `"no_hardhat"` strings across multiple files (current approach with `PPE_CLASSES`, `VIOLATION_CLASSES`, `COMPLIANT_CLASSES`).
**Why bad:** The new model has different class names. Adding or changing classes requires editing multiple files.
**Instead:** Centralize all class definitions in `EpiConfig`. Other modules reference `epi_config.active` and the translation map.

## Scalability Considerations

| Concern | Current (1-2 people) | 5-10 people | 20+ people |
|---------|----------------------|-------------|------------|
| Zone tracking | Simple clustering works | Needs tighter distance thresholds | Consider using a second person-detection model |
| State machine memory | Negligible | Negligible (~6 states x 10 zones) | Still negligible |
| Frame processing time | ~30ms (YOLOv8n) | Same (detection time is constant) | Same |
| Alert volume | Low | Moderate | High -- consider alert batching/summarization |

## Suggested Build Order

The components have clear dependencies that dictate build order.

### Phase 1: Model Integration + EPI Config (no tracking yet)

1. **`EpiConfig`** -- standalone, no dependencies on existing code
2. **Update `SafetyDetector`** -- load HuggingFace model, map 6 new classes, filter by active EPIs
3. **`PUT/GET /api/config/epi` endpoints** -- wire to `EpiConfig`
4. **`EpiConfigPanel` frontend component** -- checkboxes calling the new API
5. **Update frame annotation** -- Portuguese labels, color coding for all 6 classes

At this point: model works, EPIs are configurable, but violation logic is still the old cooldown approach (just adapted to new class names).

### Phase 2: State Machine + Zone Tracking

6. **`PersonTracker`** -- spatial clustering + zone tracking across frames
7. **`InfractionManager`** -- state machine per zone per EPI
8. **Rewire `StreamProcessor`** -- new pipeline: detect -> track -> evaluate -> alert
9. **Remove cooldown logic from `AlertManager`** -- becomes pure storage

At this point: full per-zone per-EPI state tracking with proper infraction logic.

### Phase 3: Polish + Stability

10. **Tune hysteresis thresholds** -- adjust `CONFIRM_WEARING` / `CONFIRM_MISSING` based on real camera testing
11. **Update `Alert` model and frontend** -- show zone ID, EPI type in Portuguese, reason (never_worn vs removed)
12. **Update dashboard stats** -- per-EPI violation breakdown, per-zone compliance
13. **Fix start/stop bug** -- ensure zone and state machine state is properly reset on stop

**Rationale for this order:**
- Phase 1 delivers visible value immediately (new model, configurable EPIs) without the riskiest change (tracking)
- Phase 2 is the core algorithmic work -- isolated behind clear interfaces, testable independently
- Phase 3 is tuning and integration -- requires real camera feedback

## Sources

- [Ultralytics YOLO Multi-Object Tracking Docs](https://docs.ultralytics.com/modes/track/)
- [Tanishjain9/yolov8n-ppe-detection-6classes Model Card](https://huggingface.co/Tanishjain9/yolov8n-ppe-detection-6classes)
- [ByteTrack vs BoTSORT Comparison](https://medium.com/pixelmindx/ultralytics-yolov8-object-trackers-botsort-vs-bytetrack-comparison-d32d5c82ebf3)
- [PPE Detector: YOLO-based Architecture for PPE Detection](https://pmc.ncbi.nlm.nih.gov/articles/PMC9299268/)
- [OAM-YOLO: Real-time PPE Compliance Monitoring](https://www.sciencedirect.com/science/article/abs/pii/S0957582025013254)
- [ByteTrack Configuration (Ultralytics GitHub)](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/trackers/bytetrack.yaml)

---

*Architecture analysis: 2026-03-05*

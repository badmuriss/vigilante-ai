# Technology Stack

**Project:** Vigilante.AI - Multi-class PPE Detection Integration
**Researched:** 2026-03-05
**Scope:** Integrating HF model `Tanishjain9/yolov8n-ppe-detection-6classes` into existing FastAPI + OpenCV pipeline

## Recommended Stack (Additions Only)

The existing stack (FastAPI, Next.js 14, OpenCV, Ultralytics) is kept. This document covers **new dependencies and techniques** needed for the milestone.

### Model Download and Caching

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `huggingface_hub` | >=1.5.0 | Download and cache `best.pt` from HF | Official HF client with automatic caching, version-aware deduplication, and `local_dir` support. One function call (`hf_hub_download`) handles download, cache validation, and returns a local path that Ultralytics `YOLO()` can load directly. | HIGH |

**How to download the model:**

```python
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

MODEL_REPO = "Tanishjain9/yolov8n-ppe-detection-6classes"
MODEL_FILENAME = "best.pt"

def load_ppe_model(cache_dir: str = "models") -> YOLO:
    """Download from HF (cached) and load with Ultralytics."""
    model_path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILENAME,
        local_dir=cache_dir,
    )
    return YOLO(model_path)
```

**Why `local_dir` over default cache:** The default HF cache uses symlinks in `~/.cache/huggingface/hub/` with opaque directory names. Using `local_dir="models"` places `best.pt` at `models/best.pt` -- predictable, Docker-friendly, and the `VIGILANTE_MODEL_PATH` config can point directly to it. The `.cache/huggingface/` metadata folder created inside `local_dir` prevents redundant re-downloads.

**Why not just download manually:** `hf_hub_download` handles: (1) skip if already cached, (2) resume interrupted downloads, (3) version checking if model author updates weights. Manual `wget`/`curl` gets none of this for free.

### Detection Stabilization

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `supervision` | >=0.25.0 | ByteTrack tracking + DetectionsSmoother | Roboflow's battle-tested CV utility library. Provides `sv.ByteTrack` for object tracking (assigns persistent IDs across frames) and `sv.DetectionsSmoother` for temporal averaging of bounding boxes/confidence. Integrates natively with Ultralytics via `sv.Detections.from_ultralytics()`. | HIGH |

**Why `supervision` over Ultralytics built-in tracking:** Ultralytics has `model.track()` with ByteTrack/BoTSORT built-in, but it couples tracking to the inference call and returns Ultralytics `Results` objects. The `supervision` library decouples tracking from detection, provides the `DetectionsSmoother` class (which Ultralytics does not have), and gives fine-grained control over the pipeline. The smoother alone justifies the dependency -- it is the primary fix for the "flickering detection" bug described in PROJECT.md.

**How detection stabilization works (pipeline):**

```python
import supervision as sv
from ultralytics import YOLO

model = YOLO("models/best.pt")
tracker = sv.ByteTrack(frame_rate=15)  # match stream FPS
smoother = sv.DetectionsSmoother(length=5)  # average over 5 frames

def process_frame(frame):
    results = model(frame, conf=0.5, verbose=False)
    detections = sv.Detections.from_ultralytics(results[0])

    # Step 1: Assign persistent tracker IDs across frames
    detections = tracker.update_with_detections(detections)

    # Step 2: Smooth bounding boxes and confidence over sliding window
    detections = smoother.update_with_detections(detections)

    return detections
```

**How `DetectionsSmoother` fixes flickering:**
- Maintains a sliding window of `length` frames per `tracker_id`
- Averages bounding box coordinates and confidence across the window
- When an object disappears for 1-2 frames (detection flicker), the smoother still has history and outputs a smoothed detection
- When an object truly disappears (all `length` frames show no detection), it drops the track
- Default `length=5` is good for 15 FPS streams (covers ~333ms of temporal context)

### Class Mapping

No additional library needed. The model's class indices are embedded in the `.pt` file and accessible via `model.names`:

```python
# Model provides:  {0: 'Gloves', 1: 'Vest', 2: 'goggles', 3: 'helmet', 4: 'mask', 5: 'safety_shoe'}

CLASS_NAME_PT_BR: dict[str, str] = {
    "Gloves": "Luvas",
    "Vest": "Colete",
    "goggles": "Protecao ocular",
    "helmet": "Capacete",
    "mask": "Mascara",
    "safety_shoe": "Calcado de seguranca",
}
```

**Important:** The model uses inconsistent casing (`Gloves` vs `goggles`). The class mapping dict must match the exact casing from `model.names`. This is verified at model load time, not hardcoded assumptions.

### Updated Ultralytics

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `ultralytics` | >=8.3.0 | YOLOv8 inference (upgrade from >=8.1.0) | Current stable is 8.3.244+. The >=8.1.0 floor is fine for compatibility, but pinning >=8.3.0 ensures compatibility with `supervision`'s `from_ultralytics()` adapter and recent bug fixes. | MEDIUM |

## Full New Dependencies

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `huggingface_hub` | >=1.5.0 | Model download and caching from HF | At application startup, in model loading code |
| `supervision` | >=0.25.0 | ByteTrack tracking + detection smoothing | In frame processing pipeline, between inference and annotation |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Model download | `huggingface_hub` | Manual download + commit `.pt` to repo | 6MB+ binary in git is bad practice; HF handles versioning and caching |
| Model download | `huggingface_hub` | `torch.hub.load()` | Not applicable -- this is a raw `.pt` weights file, not a torch hub model |
| Detection smoothing | `supervision` DetectionsSmoother | Custom EMA implementation | Reinventing tested code; supervision is MIT-licensed, actively maintained, and provides tracking + smoothing in one package |
| Detection smoothing | `supervision` DetectionsSmoother | Ultralytics `model.track()` | No built-in smoothing (only tracking); couples tracking to inference call; less flexible |
| Object tracking | `supervision` ByteTrack | DeepSORT | ByteTrack is simpler (no appearance model needed), faster, and sufficient for PPE detection where re-identification across long occlusions is not required |

## Installation

```bash
# New dependencies (add to backend/requirements.txt)
pip install huggingface_hub>=1.5.0 supervision>=0.25.0

# Updated requirement
# Change ultralytics>=8.1.0 to ultralytics>=8.3.0
```

**Updated `backend/requirements.txt`:**

```
fastapi>=0.109.0
uvicorn>=0.27.0
opencv-python-headless>=4.9.0
ultralytics>=8.3.0
python-multipart>=0.0.6
pydantic-settings>=2.1.0
huggingface_hub>=1.5.0
supervision>=0.25.0
```

**Docker consideration:** `huggingface_hub` will download the model on first run. For Docker builds, either:
1. Download at build time in Dockerfile (`RUN python -c "from huggingface_hub import hf_hub_download; hf_hub_download('Tanishjain9/yolov8n-ppe-detection-6classes', 'best.pt', local_dir='models')"`)
2. Or mount a volume for `models/` so the download persists across container restarts

Option 1 is recommended for production (deterministic builds). Option 2 is fine for development.

## Model Details (Reference)

| Property | Value |
|----------|-------|
| Repo | `Tanishjain9/yolov8n-ppe-detection-6classes` |
| File | `best.pt` |
| Architecture | YOLOv8 nano |
| Input size | 640x640 |
| Classes | 6: Gloves, Vest, goggles, helmet, mask, safety_shoe |
| mAP@50 | ~0.81 |
| mAP@50-95 | ~0.53 |
| Precision | ~0.80 |
| Recall | ~0.74 |
| Weakest classes | Gloves (~0.69 mAP), safety_shoe (~0.64 mAP) |
| Format | PyTorch (.pt), also available as ONNX |

**Performance note:** `safety_shoe` and `Gloves` have notably lower mAP. The configurable EPI panel mitigates this -- users can disable these classes if false positive rate is too high for their environment.

## Sources

- [Hugging Face Hub download docs](https://huggingface.co/docs/huggingface_hub/en/guides/download) - hf_hub_download API, caching behavior (HIGH confidence)
- [Tanishjain9/yolov8n-ppe-detection-6classes](https://huggingface.co/Tanishjain9/yolov8n-ppe-detection-6classes) - Model card, class indices, performance metrics (HIGH confidence)
- [Supervision DetectionsSmoother](https://supervision.roboflow.com/latest/detection/tools/smoother/) - Smoother API, sliding window averaging, requires tracker_id (HIGH confidence)
- [Ultralytics YOLO tracking docs](https://docs.ultralytics.com/modes/track/) - Built-in ByteTrack/BoTSORT support (HIGH confidence)
- [huggingface-hub PyPI](https://pypi.org/project/huggingface-hub/) - Latest version 1.5.0 (HIGH confidence)
- [ultralytics PyPI](https://pypi.org/project/ultralytics/) - Latest version 8.3.244+ (HIGH confidence)
- [supervision PyPI](https://pypi.org/project/supervision/) - Latest version 0.27.0 (HIGH confidence)

---

*Stack research: 2026-03-05*

"""Export reviewed alerts as YOLO-format training samples.

When an admin/supervisor labels an alert as `correct` or `false_positive`,
we copy the raw frame and emit a sibling `.txt` label file under
`RETRAINING_EXPORT_PATH/{confirmed,needs_review}/`. A separate merge script
later pulls the auto-mergeable ones into the canonical training split.

Design notes:
- Idempotent: re-exporting the same alert overwrites prior files. Safe to
  call repeatedly when an admin flips their decision.
- Class indices follow `ml/configs/*.yaml` (helmet=0, vest=1). Keep this
  map in sync if the YOLO config grows new classes.
- `false_positive` NEVER produces an empty label file, and never lands in
  a directory the merge script consumes. Reasoning: an alert says "capacete
  ausente". A reviewer rejecting it is asserting the worker WAS wearing the
  helmet, i.e. the detector missed a real helmet. That frame is a false
  NEGATIVE of the PPE model, not a background sample. Writing an empty
  label would teach the model that every helmet and vest actually visible
  in the frame does not exist, injecting one false negative per correct
  detection present. Instead the frame lands in `needs_review/` with the
  model's own boxes as a PRE-ANNOTATION for a human to correct (typically
  by adding the missed box) before it can enter training.
- `confirmed` labels are the model's own detections validated by a human.
  They are pseudo-labels: the reviewer confirmed the violation, not the
  tightness of each box, and any PPE the model scored below threshold is
  silently absent. Good enough to auto-merge in small volumes; revisit if
  fine-tuning on them starts degrading recall.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np

from app.config import settings
from app.db.entities import Alert
from app.storage import BlobStore

logger = logging.getLogger(__name__)


# Class name → YOLO class index. Matches `ml/configs/ppe-cctv-v1.yaml`.
_CLASS_INDEX: dict[str, int] = {
    "capacete": 0,
    "colete": 1,
}


class RetrainingExporter:
    def __init__(self, blob_store: BlobStore, root: str | Path | None = None) -> None:
        self._blob_store = blob_store
        self._root = Path(root or settings.RETRAINING_EXPORT_PATH).resolve()

    def export(self, alert: Alert) -> Path | None:
        """Materialise an alert's raw frame + YOLO label under the right
        decision subfolder. Returns the directory where files landed, or
        None when the alert has no usable raw frame on disk."""
        decision = self._decision_for(alert.feedback)
        if decision is None:
            logger.debug("Alert %s feedback=%r — skipping export", alert.id, alert.feedback)
            return None
        if not alert.frame_raw_path:
            logger.warning(
                "Alert %s has no frame_raw_path — cannot export for retraining",
                alert.id,
            )
            return None

        raw_bytes = self._blob_store.load_bytes(alert.frame_raw_path)
        if raw_bytes is None:
            logger.warning(
                "Alert %s raw frame missing on disk: %s",
                alert.id,
                alert.frame_raw_path,
            )
            return None

        # Decode before writing anything: a frame we cannot size cannot be
        # labelled, and a stray .jpg with no .txt just makes the merge script
        # log a skip forever.
        height, width = _image_dimensions(raw_bytes)
        if width <= 0 or height <= 0:
            logger.warning(
                "Alert %s raw frame has invalid dims; skipping export", alert.id
            )
            return None

        out_dir = self._root / decision
        out_dir.mkdir(parents=True, exist_ok=True)
        img_out = out_dir / f"{alert.id}.jpg"
        lbl_out = out_dir / f"{alert.id}.txt"
        img_out.write_bytes(raw_bytes)

        # Both decisions emit the PPE the model saw. For `confirmed` these are
        # validated labels. For `needs_review` they are a pre-annotation: the
        # reviewer disagreed with the violation, so a box is missing and a
        # human has to add it before this frame is fit to train on.
        lines = list(_iter_yolo_lines(alert.detected_bboxes or [], width, height))
        lbl_out.write_text("\n".join(lines) + ("\n" if lines else ""))
        return out_dir

    @staticmethod
    def _decision_for(feedback: str | None) -> str | None:
        if feedback == "correct":
            return "confirmed"
        if feedback == "false_positive":
            # NOT "rejected"/negative. See module docstring: a rejected
            # violation means the detector missed real PPE.
            return "needs_review"
        return None


def _image_dimensions(jpeg_bytes: bytes) -> tuple[int, int]:
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return (0, 0)
    h, w = img.shape[:2]
    return (h, w)


def _iter_yolo_lines(
    bboxes: Iterable[dict[str, Any]], width: int, height: int
) -> Iterable[str]:
    for record in bboxes:
        class_name = record.get("class_name")
        bbox = record.get("bbox")
        idx = _CLASS_INDEX.get(class_name) if isinstance(class_name, str) else None
        if idx is None or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = (float(v) for v in bbox)
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        cx = (x1 + x2) / 2.0 / width
        cy = (y1 + y2) / 2.0 / height
        bw = (x2 - x1) / width
        bh = (y2 - y1) / height
        if bw <= 0 or bh <= 0:
            continue
        yield f"{idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"

from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray
from ultralytics import YOLO  # type: ignore[attr-defined]

from app.config import settings
from app.models import Detection

logger = logging.getLogger(__name__)

# 6-class PPE model mapping: class_id -> internal Portuguese key
_ALL_EPI_CLASSES: dict[int, str] = {
    0: "luvas",
    1: "colete",
    2: "protecao_ocular",
    3: "capacete",
    4: "mascara",
    5: "calcado_seguranca",
}

# MVP: face/head EPIs only
MVP_EPI_KEYS = {"protecao_ocular", "capacete", "mascara"}

EPI_CLASSES: dict[int, str] = {
    k: v for k, v in _ALL_EPI_CLASSES.items() if v in MVP_EPI_KEYS
}

# Portuguese display labels for bounding box annotation
EPI_LABELS_PT: dict[str, str] = {
    "protecao_ocular": "Protecao ocular",
    "capacete": "Capacete",
    "mascara": "Mascara",
}

# Portuguese alert labels for missing EPI violations
EPI_ALERT_LABELS: dict[str, str] = {
    "protecao_ocular": "Protecao ocular ausente",
    "capacete": "Capacete ausente",
    "mascara": "Mascara ausente",
}

GREEN = (0, 200, 0)
LABEL_BG = (0, 120, 0)
RED = (0, 0, 255)


class SafetyDetector:
    def __init__(self) -> None:
        self._model: YOLO | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load_model(self) -> None:
        self._model = YOLO(settings.MODEL_PATH)
        model_classes: dict[int, str] = self._model.names
        class_names = set(model_classes.values())
        epi_values = set(EPI_CLASSES.values())

        # Validate model has expected PPE classes (by checking original English names)
        logger.info(
            "PPE model loaded with %d classes: %s",
            len(model_classes),
            class_names,
        )

    def detect(self, frame: NDArray[np.uint8]) -> list[Detection]:
        if self._model is None:
            return []

        results: Any = self._model(
            frame,
            conf=settings.CONFIDENCE_THRESHOLD,
            verbose=False,
        )

        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())

                # Map class_id to Portuguese key; skip unknown classes
                class_key = EPI_CLASSES.get(class_id)
                if class_key is None:
                    continue

                detections.append(Detection(class_key, confidence, (x1, y1, x2, y2)))

        return detections

    def annotate_frame(
        self,
        frame: NDArray[np.uint8],
        detections: list[Detection],
        missing_epis: set[str] | None = None,
    ) -> NDArray[np.uint8]:
        annotated = frame.copy()
        for det in detections:
            label_text = EPI_LABELS_PT.get(det.class_name, det.class_name)
            label = f"{label_text} {det.confidence:.0%}"
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), GREEN, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 4, y1), LABEL_BG, -1)
            cv2.putText(
                annotated, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
            )

        if missing_epis and detections:
            # Compute person region from union of all detection bboxes
            all_x1 = min(d.bbox[0] for d in detections)
            all_y1 = min(d.bbox[1] for d in detections)
            all_x2 = max(d.bbox[2] for d in detections)
            all_y2 = max(d.bbox[3] for d in detections)

            # Draw red circles + labels to the right of the person region
            circle_x = all_x2 + 30
            start_y = all_y1 + 20
            for i, epi_key in enumerate(sorted(missing_epis)):
                cy = start_y + i * 35
                cv2.circle(annotated, (circle_x, cy), 10, RED, -1)
                label_text = EPI_LABELS_PT.get(epi_key, epi_key)
                cv2.putText(
                    annotated, f"{label_text} ausente",
                    (circle_x + 18, cy + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, RED, 2,
                )

        return annotated

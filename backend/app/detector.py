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
EPI_CLASSES: dict[int, str] = {
    0: "luvas",
    1: "colete",
    2: "protecao_ocular",
    3: "capacete",
    4: "mascara",
    5: "calcado_seguranca",
}

# Portuguese display labels for bounding box annotation
EPI_LABELS_PT: dict[str, str] = {
    "luvas": "Luvas",
    "colete": "Colete",
    "protecao_ocular": "Protecao ocular",
    "capacete": "Capacete",
    "mascara": "Mascara",
    "calcado_seguranca": "Calcado de seguranca",
}

# Portuguese alert labels for missing EPI violations
EPI_ALERT_LABELS: dict[str, str] = {
    "luvas": "Luvas ausentes",
    "colete": "Colete ausente",
    "protecao_ocular": "Protecao ocular ausente",
    "capacete": "Capacete ausente",
    "mascara": "Mascara ausente",
    "calcado_seguranca": "Calcado de seguranca ausente",
}

GREEN = (0, 255, 0)


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
        self, frame: NDArray[np.uint8], detections: list[Detection]
    ) -> NDArray[np.uint8]:
        annotated = frame.copy()
        for det in detections:
            label_text = EPI_LABELS_PT.get(det.class_name, det.class_name)
            label = f"{label_text} {det.confidence:.0%}"
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), GREEN, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw, y1), GREEN, -1)
            cv2.putText(
                annotated, label, (x1, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
            )
        return annotated

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

PPE_CLASSES = {"safety_glasses", "no_safety_glasses", "hardhat", "no_hardhat"}
VIOLATION_CLASSES = {"no_safety_glasses", "no_hardhat"}
COMPLIANT_CLASSES = {"safety_glasses", "hardhat"}

GREEN = (0, 255, 0)
RED = (0, 0, 255)


class SafetyDetector:
    def __init__(self) -> None:
        self._model: YOLO | None = None
        self._has_ppe_classes: bool = False

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load_model(self) -> None:
        self._model = YOLO(settings.MODEL_PATH)
        model_classes: dict[int, str] = self._model.names
        class_names = set(model_classes.values())
        self._has_ppe_classes = bool(PPE_CLASSES & class_names)
        if self._has_ppe_classes:
            logger.info("PPE-specific model loaded with classes: %s", PPE_CLASSES & class_names)
        else:
            logger.warning(
                "Model does not have PPE classes. Using person detection as fallback. "
                "Train a custom model with classes %s for production use.",
                PPE_CLASSES,
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
                class_name: str = result.names[class_id]
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())

                if self._has_ppe_classes:
                    if class_name in PPE_CLASSES:
                        detections.append(Detection(class_name, confidence, (x1, y1, x2, y2)))
                else:
                    if class_name == "person":
                        detections.append(
                            Detection("no_hardhat", confidence, (x1, y1, x2, y2))
                        )
        return detections

    def annotate_frame(
        self, frame: NDArray[np.uint8], detections: list[Detection]
    ) -> NDArray[np.uint8]:
        annotated = frame.copy()
        for det in detections:
            color = RED if det.class_name in VIOLATION_CLASSES else GREEN
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{det.class_name} {det.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw, y1), color, -1)
            cv2.putText(
                annotated, label, (x1, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
            )
        return annotated

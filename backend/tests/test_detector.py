"""Tests for SafetyDetector: 6-class PPE model, Portuguese labels, annotation.

Covers: MODL-01 (model loading), MODL-02 (Portuguese labels).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.detector import (
    EPI_CLASSES,
    EPI_LABELS_PT,
    SafetyDetector,
)
from app.models import Detection


class TestModelLoadsPpeClasses:
    """MODL-01: Detector loads the 6-class PPE model with correct class mapping."""

    def test_epi_classes_has_6_entries(self) -> None:
        """EPI_CLASSES maps 6 integer IDs to Portuguese keys."""
        assert len(EPI_CLASSES) == 6
        expected_keys = {"luvas", "colete", "protecao_ocular", "capacete", "mascara", "calcado_seguranca"}
        assert set(EPI_CLASSES.values()) == expected_keys

    def test_model_loads_ppe_classes(self) -> None:
        """SafetyDetector.load_model loads best.pt and validates class names."""
        detector = SafetyDetector()

        # Mock YOLO so we don't need the real model file
        mock_model = MagicMock()
        mock_model.names = {
            0: "Gloves", 1: "Vest", 2: "goggles",
            3: "helmet", 4: "mask", 5: "safety_shoe",
        }

        with patch("app.detector.YOLO", return_value=mock_model):
            detector.load_model()

        assert detector.is_loaded

    def test_detect_maps_class_ids_to_portuguese(self) -> None:
        """detect() maps class_id via EPI_CLASSES to Portuguese key names."""
        detector = SafetyDetector()

        # Set up mock model
        mock_model = MagicMock()
        mock_model.names = {
            0: "Gloves", 1: "Vest", 2: "goggles",
            3: "helmet", 4: "mask", 5: "safety_shoe",
        }

        # Create mock detection result
        mock_box = MagicMock()
        mock_box.cls = [MagicMock()]
        mock_box.cls[0].item.return_value = 3  # helmet -> capacete
        mock_box.conf = [MagicMock()]
        mock_box.conf[0].item.return_value = 0.92
        mock_box.xyxy = [MagicMock()]
        mock_box.xyxy[0].tolist.return_value = [10.0, 20.0, 100.0, 200.0]

        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        mock_result.names = mock_model.names

        mock_model.return_value = [mock_result]

        with patch("app.detector.YOLO", return_value=mock_model):
            detector.load_model()

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect(frame)

        assert len(detections) == 1
        assert detections[0].class_name == "capacete"
        assert detections[0].confidence == pytest.approx(0.92)

    def test_detect_skips_unknown_class_ids(self) -> None:
        """detect() skips class_ids not in EPI_CLASSES."""
        detector = SafetyDetector()

        mock_model = MagicMock()
        mock_model.names = {0: "Gloves", 99: "unknown"}

        mock_box = MagicMock()
        mock_box.cls = [MagicMock()]
        mock_box.cls[0].item.return_value = 99  # Not in EPI_CLASSES
        mock_box.conf = [MagicMock()]
        mock_box.conf[0].item.return_value = 0.8
        mock_box.xyxy = [MagicMock()]
        mock_box.xyxy[0].tolist.return_value = [10.0, 20.0, 100.0, 200.0]

        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        mock_result.names = mock_model.names

        mock_model.return_value = [mock_result]

        with patch("app.detector.YOLO", return_value=mock_model):
            detector.load_model()

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect(frame)

        assert len(detections) == 0


class TestPortugueseLabels:
    """MODL-02: Detection labels are mapped to Portuguese."""

    def test_portuguese_labels_mapping(self) -> None:
        """EPI_LABELS_PT has a display label for every EPI class."""
        for key in EPI_CLASSES.values():
            assert key in EPI_LABELS_PT, f"Missing Portuguese label for {key}"
            assert EPI_LABELS_PT[key], f"Empty label for {key}"

    def test_labels_are_capitalized_portuguese(self) -> None:
        """Portuguese labels start with uppercase and use correct translations."""
        expected = {
            "luvas": "Luvas",
            "colete": "Colete",
            "protecao_ocular": "Protecao ocular",
            "capacete": "Capacete",
            "mascara": "Mascara",
            "calcado_seguranca": "Calcado de seguranca",
        }
        assert EPI_LABELS_PT == expected


class TestAnnotateFrame:
    """Annotation uses green color and Portuguese labels."""

    def test_annotate_uses_green_and_portuguese(self) -> None:
        """annotate_frame renders Portuguese label + confidence with green boxes."""
        detector = SafetyDetector()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        detections = [
            Detection(class_name="capacete", confidence=0.92, bbox=(10, 50, 100, 200)),
        ]

        annotated = detector.annotate_frame(frame, detections)

        # Annotated frame should differ from original (has drawn rectangles/text)
        assert not np.array_equal(annotated, frame)

        # Check that green pixels exist (OpenCV uses BGR: green = (0, 255, 0))
        green_mask = (annotated[:, :, 1] == 255) & (annotated[:, :, 0] == 0) & (annotated[:, :, 2] == 0)
        assert green_mask.any(), "Expected green color in annotation"

        # No red pixels should exist (we removed RED constant)
        red_mask = (annotated[:, :, 2] == 255) & (annotated[:, :, 0] == 0) & (annotated[:, :, 1] == 0)
        assert not red_mask.any(), "Should not have red color in annotation"

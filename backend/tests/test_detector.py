"""Tests for SafetyDetector: 4-class PPE model, Portuguese labels, annotation.

Scope is capacete + colete (canteiro civil) plus the two VIOLATION classes
(cabeca_descoberta / sem_colete) that make a violation positively detectable
instead of inferred from the absence of PPE. oculos/mascara/luvas/botas were
dropped from the model on purpose, see docs/roadmap-tcc-outubro-2026.md.

Covers: MODL-01 (model loading), MODL-02 (Portuguese labels).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.detector import (
    ALL_CLASS_LABELS_PT,
    EPI_CLASSES,
    EPI_LABELS_PT,
    GREEN,
    LABEL_BG,
    RED,
    VIOLATION_OF,
    SafetyDetector,
)
from app.models import Detection

# Class names of the legacy 2-class weights, still shipped as backend/best.pt.
MODEL_NAMES = {0: "helmet", 1: "vest"}
# Class names of the 4-class weights (ml/prepare/merge_datasets.py).
MODEL_NAMES_4 = {0: "helmet", 1: "vest", 2: "head", 3: "no_vest"}


def _load(names: dict[int, str]) -> SafetyDetector:
    detector = SafetyDetector()
    mock_model = MagicMock()
    mock_model.names = names
    with patch("app.detector.YOLO", return_value=mock_model):
        detector.load_model()
    return detector


class TestModelLoadsPpeClasses:
    """MODL-01: Detector loads the PPE model with correct class mapping."""

    def test_epi_classes_has_4_entries(self) -> None:
        """EPI_CLASSES maps the 4 weight indices to Portuguese keys."""
        assert EPI_CLASSES == {
            0: "capacete",
            1: "colete",
            2: "cabeca_descoberta",
            3: "sem_colete",
        }

    def test_old_2class_weights_still_load(self) -> None:
        """backend/best.pt is still the 2-class model: it must load, map both
        classes, and report that it cannot detect violations directly."""
        detector = _load(MODEL_NAMES)

        assert detector.is_loaded
        assert detector._class_map == {0: "capacete", 1: "colete"}
        assert detector.has_violation_classes is False

    def test_4class_weights_map_violations(self) -> None:
        detector = _load(MODEL_NAMES_4)

        assert detector._class_map == {
            0: "capacete",
            1: "colete",
            2: "cabeca_descoberta",
            3: "sem_colete",
        }
        assert detector.has_violation_classes is True

    def test_class_map_follows_names_not_indices(self) -> None:
        """Weights that order the classes differently still map correctly —
        the mapping is by name, so a reordered export cannot silently swap
        helmet and vest."""
        detector = _load({0: "no_vest", 1: "Hard-Hat", 2: "Safety Vest"})

        assert detector._class_map == {
            0: "sem_colete",
            1: "capacete",
            2: "colete",
        }

    def test_unknown_class_name_does_not_crash(self) -> None:
        """An unrecognised name falls back to the positional default instead
        of blowing up model loading."""
        detector = _load({0: "helmet", 1: "mystery_class"})

        assert detector.is_loaded
        assert detector._class_map == {0: "capacete", 1: "colete"}

    def test_model_loads_ppe_classes(self) -> None:
        """SafetyDetector.load_model loads best.pt and validates class names."""
        detector = _load(MODEL_NAMES)

        assert detector.is_loaded

    def test_detect_maps_class_ids_to_portuguese(self) -> None:
        """detect() maps class_id via EPI_CLASSES to Portuguese key names."""
        detector = SafetyDetector()

        # Set up mock model
        mock_model = MagicMock()
        mock_model.names = MODEL_NAMES

        # Create mock detection result
        mock_box = MagicMock()
        mock_box.cls = [MagicMock()]
        mock_box.cls[0].item.return_value = 0  # helmet -> capacete
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
        mock_model.names = MODEL_NAMES

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
        """Every class the model can emit has a display label."""
        for key in EPI_CLASSES.values():
            assert key in ALL_CLASS_LABELS_PT, f"Missing Portuguese label for {key}"
            assert ALL_CLASS_LABELS_PT[key], f"Empty label for {key}"

    def test_labels_are_capitalized_portuguese(self) -> None:
        """Portuguese labels start with uppercase and use correct translations."""
        assert EPI_LABELS_PT == {"capacete": "Capacete", "colete": "Colete"}

    def test_violation_classes_are_not_selectable_epis(self) -> None:
        """Violations are evidence, not equipment: they must stay out of the
        user-facing EPI toggle list that main.py builds from EPI_LABELS_PT."""
        assert set(VIOLATION_OF) == {"cabeca_descoberta", "sem_colete"}
        assert not set(VIOLATION_OF) & set(EPI_LABELS_PT)
        assert set(VIOLATION_OF.values()) == set(EPI_LABELS_PT)


def _has_color(frame: np.ndarray, bgr: tuple[int, int, int]) -> bool:
    """True if any pixel is exactly this BGR triple (no antialiasing is used)."""
    return bool((frame == np.array(bgr, dtype=np.uint8)).all(axis=2).any())


class TestAnnotateFrame:
    """Annotation uses green color and Portuguese labels."""

    def test_annotate_uses_green_and_portuguese(self) -> None:
        """annotate_frame draws a green box + green label chip, no red, when
        nothing is missing."""
        detector = SafetyDetector()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        detections = [
            Detection(class_name="capacete", confidence=0.92, bbox=(10, 50, 100, 200)),
        ]

        annotated = detector.annotate_frame(frame, detections)

        # Annotated frame should differ from original (has drawn rectangles/text)
        assert not np.array_equal(annotated, frame)

        assert _has_color(annotated, GREEN), "Expected green bbox in annotation"
        assert _has_color(annotated, LABEL_BG), "Expected green label chip"
        assert not _has_color(annotated, RED), "No red without missing EPIs"

    def test_annotate_marks_missing_epi_in_red(self) -> None:
        """missing_epis is the only path that paints red (Portuguese label)."""
        detector = SafetyDetector()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        annotated = detector.annotate_frame(frame, [], missing_epis={"colete"})

        assert _has_color(annotated, RED), "Expected red marker for missing EPI"

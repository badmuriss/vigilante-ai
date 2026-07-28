"""RetrainingExporter: a rejected alert must never become an empty label.

An alert says "capacete ausente". A reviewer rejecting it asserts the worker
WAS wearing the helmet, so the detector missed a box. Exporting that frame
with an empty label would teach the model that every helmet and vest it did
see is absent, injecting one false negative per correct detection. These
tests pin that behaviour.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.db.entities import Alert
from app.services.retraining_exporter import RetrainingExporter


class _FakeBlobStore:
    """Minimal BlobStore: serves one in-memory JPEG for any path."""

    def __init__(self, jpeg: bytes | None) -> None:
        self._jpeg = jpeg

    def load_bytes(self, path: str) -> bytes | None:
        return self._jpeg

    def save_bytes(self, path: str, data: bytes) -> str:  # pragma: no cover
        return path


def _jpeg(width: int = 640, height: int = 480) -> bytes:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame)
    assert ok
    return bytes(buf)


def _alert(feedback: str, bboxes: list[dict] | None = None) -> Alert:
    alert = Alert()
    alert.id = "alert-1"
    alert.feedback = feedback
    alert.frame_raw_path = "alerts/alert-1_frame.jpg"
    # Two helmets the model DID see, in a frame whose alert fired because a
    # third worker had none.
    alert.detected_bboxes = bboxes if bboxes is not None else [
        {"class_name": "capacete", "bbox": [10, 10, 50, 50], "confidence": 0.9},
        {"class_name": "colete", "bbox": [100, 100, 160, 220], "confidence": 0.8},
    ]
    return alert


def _exporter(tmp_path: Path, jpeg: bytes | None = None) -> RetrainingExporter:
    return RetrainingExporter(_FakeBlobStore(jpeg or _jpeg()), root=tmp_path)


def test_rejected_alert_never_writes_an_empty_label(tmp_path: Path) -> None:
    """The regression this module exists for."""
    out = _exporter(tmp_path).export(_alert("false_positive"))

    assert out is not None
    label = out / "alert-1.txt"
    assert label.read_text().strip() != "", "empty label poisons the dataset"
    assert len(label.read_text().strip().splitlines()) == 2


def test_rejected_alert_lands_outside_the_auto_merged_directory(tmp_path: Path) -> None:
    out = _exporter(tmp_path).export(_alert("false_positive"))

    assert out == tmp_path / "needs_review"
    # merge_feedback.sh only consumes confirmed/. Nothing rejected may reach it.
    assert not (tmp_path / "confirmed").exists()
    assert not (tmp_path / "rejected").exists()


def test_confirmed_alert_still_auto_merges_with_its_boxes(tmp_path: Path) -> None:
    out = _exporter(tmp_path).export(_alert("correct"))

    assert out == tmp_path / "confirmed"
    lines = (out / "alert-1.txt").read_text().strip().splitlines()
    assert [line.split()[0] for line in lines] == ["0", "1"], "helmet=0, vest=1"
    assert (out / "alert-1.jpg").exists()


def test_undecided_alert_is_not_exported(tmp_path: Path) -> None:
    assert _exporter(tmp_path).export(_alert("none")) is None
    assert list(tmp_path.iterdir()) == []


def test_undecodable_frame_leaves_no_orphan_image(tmp_path: Path) -> None:
    """A frame we cannot size cannot be labelled, so nothing is written."""
    assert _exporter(tmp_path, jpeg=b"not-a-jpeg").export(_alert("correct")) is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("feedback", ["correct", "false_positive"])
def test_bboxes_are_normalised_to_yolo_format(tmp_path: Path, feedback: str) -> None:
    alert = _alert(
        feedback,
        bboxes=[{"class_name": "capacete", "bbox": [0, 0, 320, 240], "confidence": 0.9}],
    )
    out = _exporter(tmp_path).export(alert)

    assert out is not None
    cls, cx, cy, bw, bh = (out / "alert-1.txt").read_text().split()
    # 640x480 frame, box covers the top-left quadrant.
    assert cls == "0"
    assert (float(cx), float(cy)) == pytest.approx((0.25, 0.25))
    assert (float(bw), float(bh)) == pytest.approx((0.5, 0.5))

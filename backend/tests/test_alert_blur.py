"""Unit tests for face blurring on the human-facing alert artefacts.

Covers `alert_service._blur_faces`:
- pixels inside the box change
- pixels outside the box are byte-identical
- the input frame is never mutated
- a box that overflows the frame is clipped instead of raising
- a degenerate box (zero/negative side) is ignored instead of raising

Pure numpy + cv2, no DB and no fixtures.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from app.services.alert_service import _blur_faces


def _frame() -> NDArray[np.uint8]:
    """Black frame with a white patch, so any box straddling the patch edge
    contains a hard edge (a fully uniform region would survive a blur
    unchanged and the test would prove nothing)."""
    frame: NDArray[np.uint8] = np.zeros((100, 120, 3), dtype=np.uint8)
    frame[20:60, 20:60] = 255
    return frame


BOX = (40, 40, 80, 80)  # straddles the white patch edge at x=60 / y=60


def test_blur_changes_pixels_inside_box() -> None:
    frame = _frame()
    out = _blur_faces(frame, [BOX])
    x1, y1, x2, y2 = BOX
    assert not np.array_equal(out[y1:y2, x1:x2], frame[y1:y2, x1:x2])


def test_blur_leaves_pixels_outside_box_identical() -> None:
    frame = _frame()
    out = _blur_faces(frame, [BOX])
    x1, y1, x2, y2 = BOX
    mask = np.ones(frame.shape[:2], dtype=bool)
    mask[y1:y2, x1:x2] = False
    assert np.array_equal(out[mask], frame[mask])


def test_blur_does_not_mutate_original() -> None:
    frame = _frame()
    before = frame.copy()
    out = _blur_faces(frame, [BOX])
    assert np.array_equal(frame, before)
    assert out is not frame


@pytest.mark.parametrize(
    ("box", "clipped"),
    [
        ((40, 40, 400, 300), (40, 40, 120, 100)),  # overflows right/bottom
        ((-30, -30, 40, 40), (0, 0, 40, 40)),  # negative origin
    ],
)
def test_box_outside_frame_is_clipped(
    box: tuple[int, int, int, int], clipped: tuple[int, int, int, int]
) -> None:
    frame = _frame()
    out = _blur_faces(frame, [box])  # must not raise / must not overflow
    assert out.shape == frame.shape
    x1, y1, x2, y2 = clipped
    # blurred inside the clipped rect, untouched everywhere else
    assert not np.array_equal(out[y1:y2, x1:x2], frame[y1:y2, x1:x2])
    mask = np.ones(frame.shape[:2], dtype=bool)
    mask[y1:y2, x1:x2] = False
    assert np.array_equal(out[mask], frame[mask])


@pytest.mark.parametrize(
    "box",
    [
        (50, 50, 50, 70),  # zero width
        (50, 50, 70, 50),  # zero height
        (70, 70, 50, 50),  # negative width and height
        (200, 200, 260, 260),  # entirely outside the frame
    ],
)
def test_degenerate_box_is_ignored(box: tuple[int, int, int, int]) -> None:
    frame = _frame()
    out = _blur_faces(frame, [box])
    assert np.array_equal(out, frame)


def test_no_boxes_returns_untouched_copy() -> None:
    frame = _frame()
    for boxes in (None, []):
        out = _blur_faces(frame, boxes)
        assert np.array_equal(out, frame)
        assert out is not frame


def test_small_box_still_blurs_with_valid_odd_kernel() -> None:
    """A 4px face used to be the crash case: kernel must stay odd and >= 3."""
    frame = _frame()
    out = _blur_faces(frame, [(58, 58, 62, 62)])
    assert not np.array_equal(out, frame)


def test_head_zone_is_the_top_slice_of_the_person_box() -> None:
    """Anonymisation must not depend on the frontal face cascade.

    Measured on real alert frames it returned 0 faces at every minSize, so an
    alert relying on it ships an unblurred worker. The head zone is derived
    from the person box instead, and is the same geometry the helmet
    association uses so the two cannot drift.
    """
    from app.stream import HEAD_ZONE_FRACTION, _head_zone

    x1, y1, x2, y2 = 100, 200, 180, 500  # 300px tall person
    zone = _head_zone((x1, y1, x2, y2))

    assert zone[0] == x1 and zone[2] == x2, "full width of the person"
    assert zone[1] == y1, "starts at the top of the person"
    assert zone[3] == y1 + int(300 * HEAD_ZONE_FRACTION)
    assert zone[3] < y2, "never covers the whole body"


def test_head_zone_survives_a_degenerate_person_box() -> None:
    zone = _head_zone_import()((10, 10, 12, 10))  # zero height
    assert zone[3] > zone[1], "must stay a non-empty box, never zero height"


def _head_zone_import():
    from app.stream import _head_zone

    return _head_zone

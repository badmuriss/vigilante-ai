"""Class-mapping checks for merge_datasets.

The dangerous failure here is silent and inverts a label: 'NO-Hardhat' getting
contains-matched to 'hardhat' would annotate a bare head as a helmet, teaching
the model that an uncovered head IS compliance. These asserts pin the order.

Run:  python ml/prepare/test_map_class.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.prepare.merge_datasets import TARGET_CLASSES, _to_bbox, map_class


def test_ppe_present() -> None:
    for name in ["helmet", "Hardhat", "hard-hat", "Helmet", "white_helmet"]:
        assert map_class(name) == "helmet", name
    for name in ["vest", "Safety Vest", "reflective_vest", "hi_vis"]:
        assert map_class(name) == "vest", name


def test_violations_map_to_their_own_class() -> None:
    for name in ["head", "NO-Hardhat", "No-Helmet", "no_hard_hat"]:
        assert map_class(name) == "head", name
    for name in ["NO-Safety Vest", "No-Vest"]:
        assert map_class(name) == "no_vest", name


def test_negative_never_inverts_into_the_positive_class() -> None:
    """The regression this file exists for."""
    for name in ["NO-Hardhat", "no_hardhat_v2", "NO-Safety Vest", "no_vest_2024"]:
        assert map_class(name) not in ("helmet", "vest"), name


def test_unrelated_and_junk_classes_are_dropped() -> None:
    for name in ["Gloves", "Ladder", "Safety Cone", "NO-Goggles", "-", "", "person"]:
        assert map_class(name) is None, name


def test_bbox_passes_through_untouched() -> None:
    assert _to_bbox(["0.5", "0.5", "0.2", "0.4"]) == "0.5 0.5 0.2 0.4"


def test_segmentation_polygon_collapses_to_its_bounding_box() -> None:
    """Roboflow ships polygon labels mixed in with boxes; they must not pass
    through as a 13-field row that a detection trainer silently mangles."""
    # Square polygon from (0.2,0.4) to (0.6,0.8) -> centre (0.4,0.6), 0.4 x 0.4
    poly = ["0.2", "0.4", "0.6", "0.4", "0.6", "0.8", "0.2", "0.8"]
    cx, cy, w, h = (float(v) for v in _to_bbox(poly).split())
    assert (round(cx, 4), round(cy, 4)) == (0.4, 0.6)
    assert (round(w, 4), round(h, 4)) == (0.4, 0.4)


def test_degenerate_geometry_is_dropped_not_emitted() -> None:
    assert _to_bbox(["0.5", "0.5", "0.5"]) is None          # odd count
    assert _to_bbox(["0.5", "0.5"]) is None                 # too few points
    assert _to_bbox(["0.5", "0.5", "0.5", "0.5", "0.5", "0.5"]) is None  # zero area
    assert _to_bbox(["a", "b", "c", "d", "e", "f"]) is None  # unparseable


def test_every_mapped_class_has_an_index() -> None:
    for name in ["helmet", "vest", "head", "NO-Hardhat", "NO-Safety Vest"]:
        mapped = map_class(name)
        assert mapped in TARGET_CLASSES, f"{name} -> {mapped}"


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\nTARGET_CLASSES = {TARGET_CLASSES}")

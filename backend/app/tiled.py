"""SAHI-style tiled inference for small objects.

At 960x720 a worker 58px tall wears a ~10px helmet. Whole-frame inference
letterboxes that down further and the head is gone. Slicing the frame into
overlapping tiles and feeding each tile to the model at full `imgsz` keeps
(or magnifies) the original pixels, so the helmet arrives at the network as
17-40px instead of 10.

Standalone on purpose: returns raw (class_id, confidence, xyxy) tuples and
never touches `SafetyDetector`, so the caller decides whether to apply the
per-class floors / color filter that live in detector.py.
"""

from __future__ import annotations

import numpy as np
import torch
from numpy.typing import NDArray
from torchvision.ops import batched_nms

Box = tuple[int, float, tuple[int, int, int, int]]  # class_id, conf, xyxy


def tile_offsets(length: int, tile: int, overlap: float) -> list[int]:
    """Evenly spaced tile start positions covering [0, length).

    Even spacing instead of "stride until you overshoot, then clamp the last
    one" — clamping produces a final tile that overlaps its neighbour by ~90%
    on axes only slightly longer than the tile (720 vs 640), i.e. a full extra
    forward pass for almost no new pixels.
    """
    if length <= tile:
        return [0]
    stride = max(1, int(round(tile * (1.0 - overlap))))
    n = int(np.ceil((length - tile) / stride)) + 1
    return [int(round(i * (length - tile) / (n - 1))) for i in range(n)]


def _unpack(result, ox: int, oy: int, w: int, h: int) -> list[Box]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes.xyxy) == 0:
        return []
    xyxy = boxes.xyxy.cpu().numpy()
    conf = boxes.conf.cpu().numpy()
    cls = boxes.cls.cpu().numpy()
    out: list[Box] = []
    for (x1, y1, x2, y2), c, k in zip(xyxy, conf, cls):
        out.append(
            (
                int(k),
                float(c),
                (
                    max(0, min(w, int(x1) + ox)),
                    max(0, min(h, int(y1) + oy)),
                    max(0, min(w, int(x2) + ox)),
                    max(0, min(h, int(y2) + oy)),
                ),
            )
        )
    return out


def merge_boxes(boxes: list[Box], iou: float = 0.5) -> list[Box]:
    """Class-wise NMS. An object on a tile seam is detected by both tiles."""
    if len(boxes) < 2:
        return boxes
    xyxy = torch.tensor([b[2] for b in boxes], dtype=torch.float32)
    scores = torch.tensor([b[1] for b in boxes], dtype=torch.float32)
    idxs = torch.tensor([b[0] for b in boxes], dtype=torch.int64)
    keep = batched_nms(xyxy, scores, idxs, iou)
    return [boxes[i] for i in keep.tolist()]


def tiled_detect(
    model,
    frame: NDArray[np.uint8],
    tile: int = 640,
    overlap: float = 0.2,
    conf: float = 0.10,
    imgsz: int = 640,
    iou: float = 0.5,
    include_full_frame: bool = False,
    **predict_kwargs,
) -> list[Box]:
    """Run `model` over overlapping tiles, return full-frame boxes.

    `tile` < `imgsz` upscales each crop — that is where the small-object win
    comes from. `include_full_frame` adds one whole-frame pass so large/close
    objects that no single tile contains are still found.
    """
    h, w = frame.shape[:2]
    crops: list[NDArray[np.uint8]] = []
    origins: list[tuple[int, int]] = []
    for oy in tile_offsets(h, tile, overlap):
        for ox in tile_offsets(w, tile, overlap):
            crops.append(frame[oy : oy + tile, ox : ox + tile])
            origins.append((ox, oy))
    if include_full_frame:
        crops.append(frame)
        origins.append((0, 0))

    # One batched call: N separate calls would pay N kernel-launch round trips.
    results = model(crops, conf=conf, imgsz=imgsz, verbose=False, **predict_kwargs)

    boxes: list[Box] = []
    for result, (ox, oy) in zip(results, origins):
        boxes.extend(_unpack(result, ox, oy, w, h))
    return merge_boxes(boxes, iou)


if __name__ == "__main__":
    from types import SimpleNamespace

    def _res(rows: list[tuple[int, float, tuple[float, float, float, float]]]):
        return SimpleNamespace(
            boxes=SimpleNamespace(
                xyxy=torch.tensor([r[2] for r in rows], dtype=torch.float32),
                conf=torch.tensor([r[1] for r in rows], dtype=torch.float32),
                cls=torch.tensor([r[0] for r in rows], dtype=torch.float32),
            )
            if rows
            else SimpleNamespace(
                xyxy=torch.zeros((0, 4)), conf=torch.zeros(0), cls=torch.zeros(0)
            )
        )

    frame = np.zeros((400, 1000, 3), dtype=np.uint8)
    assert tile_offsets(1000, 640, 0.2) == [0, 360], tile_offsets(1000, 640, 0.2)
    assert tile_offsets(400, 640, 0.2) == [0]

    # Tiles are x=[0,640) and x=[360,1000). Seam object at global x 480..520 is
    # inside BOTH, so the model reports it twice, in different local coords.
    class SeamModel:
        def __call__(self, crops, **_):
            assert len(crops) == 2, len(crops)
            return [
                _res([(0, 0.9, (480, 180, 520, 220))]),  # tile @ ox=0
                _res([(0, 0.8, (120, 180, 160, 220))]),  # tile @ ox=360
            ]

    merged = tiled_detect(SeamModel(), frame, tile=640, overlap=0.2)
    assert len(merged) == 1, f"seam box duplicated: {merged}"
    assert merged[0][2] == (480, 180, 520, 220), merged[0]
    assert abs(merged[0][1] - 0.9) < 1e-6, merged[0]  # NMS keeps the higher score

    # Same two tiles, genuinely different objects -> both survive.
    class TwoModel:
        def __call__(self, crops, **_):
            return [
                _res([(0, 0.9, (10, 180, 50, 220))]),  # global 10..50
                _res([(0, 0.8, (500, 180, 540, 220))]),  # global 860..900
            ]

    assert len(tiled_detect(TwoModel(), frame, tile=640, overlap=0.2)) == 2

    # Different classes at the same place are never merged.
    class TwoClassModel:
        def __call__(self, crops, **_):
            return [
                _res([(0, 0.9, (480, 180, 520, 220))]),
                _res([(1, 0.8, (120, 180, 160, 220))]),
            ]

    assert len(tiled_detect(TwoClassModel(), frame, tile=640, overlap=0.2)) == 2

    print("ok")

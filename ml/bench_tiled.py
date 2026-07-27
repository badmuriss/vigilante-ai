"""Benchmark whole-frame vs tiled (SAHI-style) inference on compliant footage.

Every worker in the webcam_raw footage wears a helmet and a vest, so on this
set MORE detections is strictly better — there is nothing to over-detect except
background. To keep "more boxes" honest, each PPE box is also checked against
person candidates: a helmet whose center is inside a person is a real recall
win, one floating in the sky is noise.

Usage:
    cd backend && PYTHONPATH=. .venv/bin/python ../ml/bench_tiled.py FRAMES_DIR
"""

from __future__ import annotations

import argparse
import glob
import statistics
import time
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

from app.config import settings
from app.detector import EPI_CLASSES
from app.tiled import tile_offsets, tiled_detect

FLOORS = {
    "capacete": settings.HELMET_CONFIDENCE_THRESHOLD,
    "colete": settings.VEST_CONFIDENCE_THRESHOLD,
}

# (label, tile, overlap, imgsz, include_full_frame)
CONFIGS = [
    ("tile640 ov0.2 @640", 640, 0.2, 640, False),
    ("tile640 ov0.2 @960", 640, 0.2, 960, False),
    ("tile480 ov0.2 @640", 480, 0.2, 640, False),
    ("tile384 ov0.2 @640", 384, 0.2, 640, False),
    ("tile384 ov0.4 @640", 384, 0.4, 640, False),
    ("tile320 ov0.2 @640", 320, 0.2, 640, False),
    ("tile384 ov0.2 @640 +full", 384, 0.2, 640, True),
]


def sync() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def whole_frame(model, frame) -> list[tuple[int, float, tuple[int, int, int, int]]]:
    """Same call detector.detect() makes: longest side -> MODEL_INPUT_SIZE."""
    h, w = frame.shape[:2]
    size = settings.MODEL_INPUT_SIZE
    scale = min(size / max(h, w), 1.0)
    img = (
        cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        if scale < 1.0
        else frame
    )
    inv = 1.0 / scale
    out = []
    for r in model(img, conf=settings.CONFIDENCE_THRESHOLD, imgsz=size, verbose=False):
        if r.boxes is None:
            continue
        for b in r.boxes:
            x1, y1, x2, y2 = (int(v * inv) for v in b.xyxy[0].tolist())
            out.append((int(b.cls[0]), float(b.conf[0]), (x1, y1, x2, y2)))
    return out


def keep(boxes):
    """Apply production per-class floors; drop classes the pipeline ignores."""
    out = []
    for cid, conf, bb in boxes:
        key = EPI_CLASSES.get(cid)
        if key is None or conf < FLOORS.get(key, settings.CONFIDENCE_THRESHOLD):
            continue
        out.append((key, conf, bb))
    return out


def in_person(bb, persons, top_frac: float = 1.0) -> bool:
    """Box center inside a person (top_frac=1.0) or their head zone (0.3)."""
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    return any(
        px1 <= cx <= px2 and py1 <= cy <= py1 + (py2 - py1) * top_frac
        for px1, py1, px2, py2 in persons
    )


def summarize(label, per_frame, times, persons_per_frame, n_tiles):
    hel = [b for f in per_frame for b in f if b[0] == "capacete"]
    ves = [b for f in per_frame for b in f if b[0] == "colete"]
    hel_hit = sum(
        1
        for f, ps in zip(per_frame, persons_per_frame)
        for b in f
        if b[0] == "capacete" and in_person(b[2], ps, 0.35)
    )
    ves_hit = sum(
        1
        for f, ps in zip(per_frame, persons_per_frame)
        for b in f
        if b[0] == "colete" and in_person(b[2], ps)
    )
    frames_with_helmet = sum(1 for f in per_frame if any(b[0] == "capacete" for b in f))
    med_h = (
        statistics.median([b[2][3] - b[2][1] for b in hel]) if hel else 0
    )
    return {
        "label": label,
        "tiles": n_tiles,
        "helmets": len(hel),
        "helmets_on_person": hel_hit,
        "vests": len(ves),
        "vests_on_person": ves_hit,
        "frames_with_helmet": frames_with_helmet,
        "median_helmet_px": round(med_h, 1),
        "ms_median": round(statistics.median(times) * 1000, 1),
        "ms_p90": round(sorted(times)[int(len(times) * 0.9)] * 1000, 1),
    }


def false_alarm_section(model, person_model, imgs) -> None:
    """The product metric: every worker here IS compliant, so any `missing`
    verdict is a false alarm. Combines tiled/whole person detection with
    tiled/whole PPE detection and replays stream._evaluate_person."""
    from app.models import Detection
    import app.stream as stream

    def persons_whole(img):
        h, w = img.shape[:2]
        r = person_model(img, classes=[0], conf=settings.PERSON_CONFIDENCE_THRESHOLD,
                         imgsz=settings.PERSON_INPUT_SIZE, verbose=False)[0]
        out = []
        for b in r.boxes:
            x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
            bw, bh = max(1, x2 - x1), max(1, y2 - y1)
            if bh / bw < settings.PERSON_MIN_ASPECT_RATIO:
                continue
            if (bw * bh) / (h * w) < settings.PERSON_MIN_AREA_RATIO:
                continue
            out.append((x1, y1, x2, y2))
        return out

    def persons_tiled(img):
        out = []
        for _, _, (x1, y1, x2, y2) in tiled_detect(
            person_model, img, tile=320, overlap=0.2, conf=0.30, imgsz=640, classes=[0]
        ):
            bw, bh = max(1, x2 - x1), max(1, y2 - y1)
            if bh / bw < settings.PERSON_MIN_ASPECT_RATIO:
                continue
            out.append((x1, y1, x2, y2))
        return out

    def ppe_whole(img):
        return [Detection(k, c, b) for k, c, b in keep(whole_frame(model, img))]

    def ppe_tiled(img):
        return [
            Detection(k, c, b)
            for k, c, b in keep(
                tiled_detect(model, img, tile=384, overlap=0.2,
                             conf=settings.CONFIDENCE_THRESHOLD, imgsz=640,
                             include_full_frame=True)
            )
        ]

    combos = [
        ("whole person + whole PPE (production)", persons_whole, ppe_whole),
        ("whole person + tiled PPE", persons_whole, ppe_tiled),
        ("tiled person + whole PPE", persons_tiled, ppe_whole),
        ("tiled person + tiled PPE", persons_tiled, ppe_tiled),
    ]
    orig_gate = stream.HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX
    print(f"\n\nFALSE ALARMS (all workers compliant -> every 'missing' is wrong)")
    hdr = f"{'combo':<40}{'gate':>6}{'persons':>9}{'hel-chk':>9}{'hel-FA':>8}{'hel-FA%':>9}{'vest-FA%':>10}"
    print(hdr)
    print("-" * len(hdr))
    for gate in (orig_gate, 30):
        stream.HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX = gate
        for label, pf, df in combos:
            n_person = n_hel_chk = n_hel_fa = n_vest = n_vest_fa = 0
            for img in imgs:
                dets = df(img)
                for pb in pf(img):
                    n_person += 1
                    ev, checkable = stream._evaluate_person(pb, dets, ACTIVE)
                    if "capacete" in checkable:
                        n_hel_chk += 1
                        n_hel_fa += "capacete" in ev.missing
                    if "colete" in checkable:
                        n_vest += 1
                        n_vest_fa += "colete" in ev.missing
            hp = f"{100 * n_hel_fa / n_hel_chk:.0f}%" if n_hel_chk else "n/a"
            vp = f"{100 * n_vest_fa / n_vest:.0f}%" if n_vest else "n/a"
            print(f"{label:<40}{gate:>6}{n_person:>9}{n_hel_chk:>9}{n_hel_fa:>8}{hp:>9}{vp:>10}")
    stream.HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX = orig_gate


ACTIVE = {"capacete", "colete"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("frames", type=Path)
    args = p.parse_args()

    files = sorted(glob.glob(str(args.frames / "*.jpg")))
    if not files:
        raise SystemExit(f"No .jpg under {args.frames}")
    imgs = [cv2.imread(f) for f in files]
    imgs = [i for i in imgs if i is not None]
    h, w = imgs[0].shape[:2]
    print(f"{len(imgs)} frames @ {w}x{h}\n")

    model = YOLO(settings.MODEL_PATH)
    person_model = YOLO(settings.PERSON_MODEL_PATH)

    # Person reference set, cached. Detected TILED on purpose: whole-frame
    # yolov8n misses half the workers in this footage (333 vs 631 boxes), which
    # would make every PPE box look like a false positive.
    persons = [
        [
            bb
            for _, _, bb in tiled_detect(
                person_model, img, tile=320, overlap=0.2, conf=0.10, imgsz=640, classes=[0]
            )
        ]
        for img in imgs
    ]
    print(f"person reference boxes (tiled320): {sum(len(p) for p in persons)}\n")

    rows = []

    for _ in range(3):  # warmup
        whole_frame(model, imgs[0])
    sync()
    per_frame, times = [], []
    for img in imgs:
        t = time.perf_counter()
        boxes = whole_frame(model, img)
        sync()
        times.append(time.perf_counter() - t)
        per_frame.append(keep(boxes))
    rows.append(summarize("whole-frame @960 (production)", per_frame, times, persons, 1))

    for label, tile, ov, imgsz, full in CONFIGS:
        n_tiles = len(tile_offsets(h, tile, ov)) * len(tile_offsets(w, tile, ov)) + int(full)
        for _ in range(3):
            tiled_detect(model, imgs[0], tile=tile, overlap=ov, conf=settings.CONFIDENCE_THRESHOLD, imgsz=imgsz, include_full_frame=full)
        sync()
        per_frame, times = [], []
        for img in imgs:
            t = time.perf_counter()
            boxes = tiled_detect(
                model, img, tile=tile, overlap=ov,
                conf=settings.CONFIDENCE_THRESHOLD, imgsz=imgsz, include_full_frame=full,
            )
            sync()
            times.append(time.perf_counter() - t)
            per_frame.append(keep(boxes))
        rows.append(summarize(label, per_frame, times, persons, n_tiles))

    hdr = f"{'config':<30}{'tiles':>6}{'helmet':>8}{'/person':>9}{'vest':>7}{'/person':>9}{'frm+hel':>9}{'medHpx':>8}{'ms':>8}{'p90ms':>8}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(
            f"{r['label']:<30}{r['tiles']:>6}{r['helmets']:>8}{r['helmets_on_person']:>9}"
            f"{r['vests']:>7}{r['vests_on_person']:>9}{r['frames_with_helmet']:>9}"
            f"{r['median_helmet_px']:>8}{r['ms_median']:>8}{r['ms_p90']:>8}"
        )

    false_alarm_section(model, person_model, imgs)


if __name__ == "__main__":
    main()

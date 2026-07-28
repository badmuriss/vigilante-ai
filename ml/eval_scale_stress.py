"""Does the model still detect violations at DEPLOYMENT scale?

In-domain metrics are measured on Roboflow frames where a bare head fills ~1%
of the image. On a real CCTV frame a worker is ~58px tall and the head is
~10-25px, two orders of magnitude smaller in area. A model can score recall
0.91 on the test split and still be blind in the field.

Compliant footage cannot answer this: it contains no violations, so zero
`head` detections is the correct output and proves nothing. This script keeps
the labels and shrinks the pixels instead — each test image is scaled down and
pasted into a 960x720 canvas, so the SAME annotated objects arrive at the size
the camera actually delivers.

Usage:
    cd backend && PYTHONPATH=. .venv/bin/python ../ml/eval_scale_stress.py \
        --weights ../ml/runs/train/ppe-cctv-v2/weights/best.pt \
        --frames  ../ml/datasets/merged4/images/test \
        --scales  1.0 0.5 0.3 0.2
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import yaml

CANVAS_W, CANVAS_H = 960, 720
NAMES = {0: "helmet", 1: "vest", 2: "head", 3: "no_vest"}


def build_scaled_split(images: Path, labels: Path, scale: float, out: Path) -> int:
    """Paste every image, shrunk by `scale`, into a CANVAS-sized grey frame.

    Grey rather than black: a black border is itself a strong edge the detector
    can key on, and it is not what a real frame looks like.
    """
    img_out, lbl_out = out / "images", out / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    kept = 0
    for src in sorted(images.iterdir()):
        lbl = labels / f"{src.stem}.txt"
        if not lbl.is_file():
            continue
        img = cv2.imread(str(src))
        if img is None:
            continue
        h, w = img.shape[:2]

        # Fit the image into the canvas first, then apply the stress factor.
        fit = min(CANVAS_W / w, CANVAS_H / h)
        f = fit * scale
        nw, nh = max(1, int(w * f)), max(1, int(h * f))
        small = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)

        canvas = np.full((CANVAS_H, CANVAS_W, 3), 114, dtype=np.uint8)
        ox, oy = (CANVAS_W - nw) // 2, (CANVAS_H - nh) // 2
        canvas[oy:oy + nh, ox:ox + nw] = small
        cv2.imwrite(str(img_out / f"{src.stem}.jpg"), canvas)

        lines = []
        for line in lbl.read_text().splitlines():
            p = line.split()
            if len(p) != 5:
                continue
            cls, cx, cy, bw, bh = p[0], *(float(v) for v in p[1:])
            # Normalised in the ORIGINAL image -> pixels -> canvas -> normalised.
            lines.append(
                f"{cls} {(cx * nw + ox) / CANVAS_W:.6f} {(cy * nh + oy) / CANVAS_H:.6f} "
                f"{bw * nw / CANVAS_W:.6f} {bh * nh / CANVAS_H:.6f}"
            )
        (lbl_out / f"{src.stem}.txt").write_text("\n".join(lines) + "\n")
        kept += 1
    return kept


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--weights", type=Path, required=True)
    p.add_argument("--frames", type=Path, required=True)
    p.add_argument("--labels", type=Path, default=None)
    p.add_argument("--scales", type=float, nargs="+", default=[1.0, 0.5, 0.3, 0.2])
    p.add_argument("--device", default="0")
    p.add_argument("--imgsz", type=int, default=960)
    args = p.parse_args()

    if not args.weights.is_file():
        raise SystemExit(f"weights not found: {args.weights}")
    images = args.frames
    labels = args.labels or Path(str(images).replace("/images/", "/labels/"))
    if not images.is_dir() or not labels.is_dir():
        raise SystemExit(f"need both {images} and {labels}")

    from ultralytics import YOLO

    model = YOLO(str(args.weights))
    rows = []
    for scale in args.scales:
        tmp = Path(tempfile.mkdtemp(prefix=f"scale{scale}_"))
        try:
            n = build_scaled_split(images, labels, scale, tmp)
            if n == 0:
                raise SystemExit(f"no image+label pairs built under {images}")
            data = tmp / "data.yaml"
            data.write_text(yaml.safe_dump({
                "path": str(tmp), "train": "images", "val": "images", "names": NAMES
            }, sort_keys=False))
            res = model.val(data=str(data), imgsz=args.imgsz, device=args.device,
                            verbose=False, plots=False)
            per = {NAMES[c]: float(res.box.r[i]) for i, c in enumerate(res.box.ap_class_index)}
            rows.append((scale, n, per))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nrecall por classe vs escala (imagem encolhida no canvas {CANVAS_W}x{CANVAS_H})")
    print(f"{'escala':>7} {'imgs':>6} | " + " ".join(f"{n:>9}" for n in NAMES.values()))
    print("-" * 60)
    for scale, n, per in rows:
        cells = " ".join(f"{per.get(name, float('nan')):>9.3f}" for name in NAMES.values())
        print(f"{scale:>7} {n:>6} | {cells}")
    print("\nescala 1.0 = imagem inteira no canvas. 0.2 = objeto 5x menor,")
    print("que e' a ordem de grandeza do gap medido entre dataset e camera real.")


if __name__ == "__main__":
    main()

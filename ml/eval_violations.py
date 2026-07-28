"""Labelled evaluation: per-class precision / recall / mAP on real footage.

The complement of ml/eval_compliant.py. That one needs no labels but can only
measure false alarms (all-compliant footage has no violations). This one needs
ground truth and measures what the compliant footage cannot: does the model
actually SEE a bare head or a missing vest when one is there?

Metrics come from ultralytics' own DetectionValidator — same code path as
training — so the numbers are comparable with what `ml/train.py` prints. The
only thing this script adds is not requiring a prepared dataset YAML: point it
at a frames directory and its YOLO .txt labels and it stages a throwaway
dataset in /tmp (symlinks, nothing is written into your dataset).

Label lookup order, first hit wins:
    --labels DIR/<same relative path>.txt
    <image path with an `images` path component swapped for `labels`>.txt
    <image dir>/<stem>.txt

Usage:
    cd backend
    PYTHONPATH=. .venv/bin/python ../ml/eval_violations.py \
        --weights ../ml/runs/train/ppe-4c/weights/best.pt \
        --frames  ../ml/datasets/merged4/images/val
    ... --labels DIR    # when labels do not sit beside/parallel to the images
    ... --out report.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

IMG_GLOBS = ("*.jpg", "*.jpeg", "*.png")


def die(msg: str) -> "None":
    raise SystemExit(f"eval_violations: {msg}")


def find_images(root: Path) -> list[Path]:
    if not root.exists():
        die(f"frames path does not exist: {root}")
    if not root.is_dir():
        die(f"frames path is not a directory: {root}")
    imgs: list[Path] = []
    for pattern in IMG_GLOBS:
        imgs.extend(root.rglob(pattern))
    if not imgs:
        die(f"no images ({'/'.join(IMG_GLOBS)}) anywhere under {root}")
    # Datasets here are symlink farms (ml/prepare/merge_datasets.py). A moved
    # repo leaves them dangling, and ultralytics quietly drops unreadable
    # images — a shrinking test set that still prints a confident mAP.
    dangling = [p for p in imgs if not p.is_file()]
    if dangling:
        sample = "\n  ".join(f"{p} -> {p.readlink()}" if p.is_symlink() else str(p)
                             for p in dangling[:5])
        die(f"{len(dangling)}/{len(imgs)} images are unreadable (dangling symlinks "
            f"after a repo move?). Refusing to score a silently shrunk test set. "
            f"First few:\n  {sample}")
    return sorted(imgs)


def label_for(img: Path, root: Path, labels_root: Path | None) -> Path | None:
    rel = img.relative_to(root).with_suffix(".txt")
    candidates = []
    if labels_root is not None:
        candidates += [labels_root / rel, labels_root / rel.name]
    parts = list(img.parts)
    if "images" in parts:
        parts[len(parts) - 1 - parts[::-1].index("images")] = "labels"
        candidates.append(Path(*parts).with_suffix(".txt"))
    candidates.append(img.with_suffix(".txt"))
    for c in candidates:
        if c.is_file():
            return c
    return None


def read_label(path: Path, nc: int) -> list[int]:
    """Class ids in one label file. Loud on malformed rows / out-of-range ids."""
    ids: list[int] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) < 5:
            die(f"{path}:{lineno} has {len(fields)} fields, YOLO format needs >= 5")
        try:
            cid = int(float(fields[0]))
        except ValueError:
            die(f"{path}:{lineno} class id {fields[0]!r} is not a number")
        if not 0 <= cid < nc:
            die(f"{path}:{lineno} class id {cid} is outside the checkpoint's "
                f"{nc} classes — labels and weights use different schemas")
        ids.append(cid)
    return ids


def stage(pairs: list[tuple[Path, Path]], root: Path, names: dict[int, str]) -> Path:
    """Symlink a flat YOLO dataset into a tempdir and return its data.yaml."""
    tmp = Path(tempfile.mkdtemp(prefix="eval_violations_"))
    (tmp / "images").mkdir()
    (tmp / "labels").mkdir()
    for img, lbl in pairs:
        flat = "__".join(img.relative_to(root).parts)
        (tmp / "images" / flat).symlink_to(img.resolve())
        (tmp / "labels" / Path(flat).with_suffix(".txt")).symlink_to(lbl.resolve())
    yaml = tmp / "data.yaml"
    yaml.write_text(
        f"path: {tmp}\ntrain: images\nval: images\nnames:\n"
        + "".join(f"  {i}: {n}\n" for i, n in sorted(names.items()))
    )
    return yaml


def self_test() -> None:
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        try:
            find_images(root)
        except SystemExit:
            pass
        else:
            raise AssertionError("find_images should reject an empty dir")

        (root / "images" / "val").mkdir(parents=True)
        (root / "labels" / "val").mkdir(parents=True)
        img = root / "images" / "val" / "a.jpg"
        img.write_bytes(b"x")
        lbl = root / "labels" / "val" / "a.txt"
        lbl.write_text("0 0.5 0.5 0.2 0.2\n3 0.1 0.1 0.1 0.1\n")

        assert find_images(root / "images") == [img]
        assert label_for(img, root / "images", None) == lbl
        assert label_for(img, root / "images", root / "labels") == lbl
        assert read_label(lbl, 4) == [0, 3]
        for nc, bad in ((2, "class id 3"), (4, None)):
            try:
                read_label(lbl, nc)
            except SystemExit:
                assert bad, "valid label rejected"
            else:
                assert not bad, "out-of-range class id accepted"

        (root / "images" / "val" / "orphan.jpg").write_bytes(b"x")
        assert label_for(root / "images" / "val" / "orphan.jpg",
                         root / "images", None) is None

        malformed = root / "labels" / "val" / "bad.txt"
        malformed.write_text("0 0.5 0.5\n")
        try:
            read_label(malformed, 4)
        except SystemExit:
            pass
        else:
            raise AssertionError("short YOLO row accepted")

        yaml = stage([(img, lbl)], root / "images", {0: "helmet", 3: "no_vest"})
        assert yaml.is_file()
        assert (yaml.parent / "images" / "val__a.jpg").is_symlink()
        assert (yaml.parent / "labels" / "val__a.txt").is_symlink()
        shutil.rmtree(yaml.parent)
    print("eval_violations self-test OK")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--weights", type=Path, help="Checkpoint to evaluate")
    p.add_argument("--frames", type=Path, help="Directory of labelled frames")
    p.add_argument("--labels", type=Path, default=None,
                   help="Label directory, when not beside/parallel to the images")
    p.add_argument("--imgsz", type=int, default=960)
    p.add_argument("--device", default="0")
    p.add_argument("--conf", type=float, default=0.001,
                   help="Validator confidence floor (0.001 = ultralytics default, "
                        "the one mAP is defined at)")
    p.add_argument("--iou", type=float, default=0.6, help="NMS IoU")
    p.add_argument("--out", type=Path, default=None, help="Write the summary as JSON")
    p.add_argument("--keep-staging", action="store_true",
                   help="Do not delete the staged /tmp dataset (debugging)")
    p.add_argument("--self-test", action="store_true",
                   help="Check the label/staging logic and exit (no model needed)")
    args = p.parse_args()

    if args.self_test:
        self_test()
        return
    if args.weights is None or args.frames is None:
        p.error("--weights and --frames are required")
    if not args.weights.is_file():
        die(f"weights not found: {args.weights.resolve()}")
    if args.labels is not None and not args.labels.is_dir():
        die(f"--labels is not a directory: {args.labels.resolve()}")

    images = find_images(args.frames)

    from ultralytics import YOLO

    model = YOLO(str(args.weights))
    names: dict[int, str] = {int(k): str(v) for k, v in model.names.items()}
    nc = len(names)

    pairs: list[tuple[Path, Path]] = []
    unlabelled: list[Path] = []
    counts = {i: 0 for i in names}
    empty_labels = 0
    for img in images:
        lbl = label_for(img, args.frames, args.labels)
        if lbl is None:
            unlabelled.append(img)
            continue
        ids = read_label(lbl, nc)
        if not ids:
            empty_labels += 1
        for cid in ids:
            counts[cid] += 1
        pairs.append((img, lbl))

    if unlabelled:
        sample = "\n  ".join(str(u) for u in unlabelled[:5])
        die(f"{len(unlabelled)}/{len(images)} images have no .txt label. "
            f"An unlabelled image counts as 'no objects here' and silently "
            f"destroys precision, so this is fatal. First few:\n  {sample}\n"
            f"Pass --labels DIR if the labels live elsewhere.")
    if not pairs:
        die("no image/label pairs to evaluate")

    missing_gt = [names[i] for i, n in counts.items() if n == 0]
    if len(missing_gt) == nc:
        die(f"every label file is empty across {len(pairs)} images — there is no "
            f"ground truth to score against")

    print(f"weights:  {args.weights.resolve()}")
    print(f"frames:   {args.frames.resolve()}")
    print(f"pairs:    {len(pairs)} image+label "
          f"({empty_labels} labels with zero objects — legitimate negatives)")
    print("gt boxes: " + ", ".join(f"{names[i]}={counts[i]}" for i in sorted(names)))
    if missing_gt:
        print(f"WARNING: no ground truth for {missing_gt} — their P/R/mAP below is "
              f"undefined, NOT a measured zero", file=sys.stderr)

    yaml = stage(pairs, args.frames, names)
    try:
        res = model.val(
            data=str(yaml),
            imgsz=args.imgsz,
            device=args.device,
            conf=args.conf,
            iou=args.iou,
            split="val",
            plots=False,
            project=str(yaml.parent),
            name="val",
            exist_ok=True,
        )

        per_class: dict[str, dict[str, float]] = {}
        idx_of = {int(c): i for i, c in enumerate(res.box.ap_class_index)}
        for cid, name in sorted(names.items()):
            if cid not in idx_of:
                per_class[name] = {"gt": counts[cid], "note": "no prediction/GT pair"}
                continue
            i = idx_of[cid]
            per_class[name] = {
                "gt": counts[cid],
                "precision": float(res.box.p[i]),
                "recall": float(res.box.r[i]),
                "mAP50": float(res.box.ap50[i]),
                "mAP50-95": float(res.box.ap[i]),
            }

        summary = {
            "weights": str(args.weights.resolve()),
            "frames": str(args.frames.resolve()),
            "images": len(pairs),
            "mAP50": float(res.box.map50),
            "mAP50-95": float(res.box.map),
            "precision": float(res.box.mp),
            "recall": float(res.box.mr),
            "per_class": per_class,
        }

        print()
        print(f"{'class':<12}{'gt':>8}{'P':>9}{'R':>9}{'mAP50':>9}{'mAP50-95':>10}")
        print("-" * 57)
        for name, m in per_class.items():
            if "precision" not in m:
                print(f"{name:<12}{m['gt']:>8}{'n/a':>9}{'n/a':>9}{'n/a':>9}{'n/a':>10}")
                continue
            print(f"{name:<12}{m['gt']:>8}{m['precision']:>9.3f}{m['recall']:>9.3f}"
                  f"{m['mAP50']:>9.3f}{m['mAP50-95']:>10.3f}")
        print("-" * 57)
        print(f"{'ALL':<12}{sum(counts.values()):>8}{summary['precision']:>9.3f}"
              f"{summary['recall']:>9.3f}{summary['mAP50']:>9.3f}"
              f"{summary['mAP50-95']:>10.3f}")

        if args.out:
            args.out.write_text(json.dumps(summary, indent=2))
            print(f"\nwrote {args.out.resolve()}")
    finally:
        if args.keep_staging:
            print(f"staging kept at {yaml.parent}")
        else:
            shutil.rmtree(yaml.parent, ignore_errors=True)


if __name__ == "__main__":
    main()

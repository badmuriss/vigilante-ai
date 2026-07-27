# Training plan — ppe-cctv-v2

Config: `ml/configs/ppe-cctv-v2.yaml`. Launch:

```bash
/home/badmuriss/Documents/vigilante-ai/backend/.venv/bin/yolo \
  cfg=/home/badmuriss/Documents/vigilante-ai/ml/configs/ppe-cctv-v2.yaml
```

Prerequisite: the 4-class merge must have finished writing `ml/datasets/merged4/`
(the config reads the `data.yaml` that `merge_datasets.py` emits there).

Every number below was measured on this machine (RTX 4070 SUPER, 11411 MiB free,
torch 2.10+cu128, ultralytics 8.4.21), not estimated.

## Why v1 failed in the field

`ppe-canteiro-v1-4` scored mAP50 0.944 on a val split built by shuffling all
pooled source frames, so near-duplicate frames from the same Roboflow video sit
on both sides of the split. It measured memorisation. Three concrete defects
compounded it, all fixed here:

1. Trained at `imgsz=640` while the backend infers at `settings.MODEL_INPUT_SIZE
   = 960`. The shipped model never saw its deployment scale.
2. Violations inferred from absence, so every miss on a 12 px helmet became an
   accusation — 100% helmet false-alarm rate on the 143 real frames.
3. Three of its augmentation settings were dead: `erasing=0.4` and
   `auto_augment` are classification-only, and `copy_paste` returns early on
   box-only labels. (`close_mosaic=10` *was* set, so mosaic did stop 10 epochs
   early — v1's flaw was that 10 epochs is too short a tail, not that it was 0.)

## Choices

**Base model — `yolov8s-p2.yaml`, COCO-pretrained.** Adds a stride-4 detection
head. Deployment helmets are ~10-25 px on a 960x720 frame; at stride 8 a 12 px
box covers ~1.5x1.5 cells and TAL has almost no candidate anchors to assign, at
stride 4 it covers ~3x3. Measured strides after build: `[4, 8, 16, 32]`.

**Not yolov8m.** Measured CPU forward at 960: yolov8s 637 ms, yolov8s-p2 679 ms
(+6.6%), yolov8m 1163 ms (+82%). `k8s/20-backend.yaml` deploys with no GPU on
purpose, so inference cost is the binding constraint — and yolov8m spends it on
depth/width when the deficit is spatial resolution. Not yolo11s either: measured
*higher* VRAM than yolov8s (8382 vs 6832 MiB at 1280/b8) and it has no P2 variant
shipped in this ultralytics version.

**Pretrained from `ml/weights/yolov8s.pt`, not `backend/best.pt`.** Measured:
both transfer exactly 5.83M of 10.66M params into the p2 graph (100% of the
backbone by name; the p2 neck/head indices shift so nothing there matches).
Identical transfer, and COCO weights carry no frontal-helmet scale bias. Note
this only works through the `yolo cfg=` CLI: `trainer.setup_model` honours a
`pretrained:` path solely when `model` is a `.yaml` — `YOLO('x.yaml').train()`
in `ml/train.py` pre-builds the module and skips that branch entirely.

**imgsz 960, batch 12.** 960 is simultaneously the backend's existing
`MODEL_INPUT_SIZE` and the native width of the webcam frames (sampled 40 of 143,
all 960x720), so the camera's pixels reach the network unscaled and train/infer
scales finally agree. Measured peak VRAM, AMP + AdamW + EMA, 8 boxes/img:

| model | imgsz | batch | peak reserved |
|---|---|---|---|
| yolov8s | 640 | 16 | 3656 MiB (v1's setting) |
| yolov8s | 960 | 16 | 7658 MiB |
| yolov8s | 1280 | 12 | 10086 MiB |
| yolov8s-p2 | 960 | 12 | **8722 MiB** |
| yolov8s-p2 | 1280 | 6 | 7740 MiB |
| yolo11m | 960 | 12 | OOM |

1280 would fit at b6 but only upsamples a 960-wide source — no new information,
1.6x the cost, and it would break parity with the backend.

**Class imbalance — oversample the rare classes, but treat it as second-order.**
Measured source totals projected onto the 4-class schema: helmet 88.5k, head
32.9k, vest 10.2k, no_vest 2.4k (37:1 worst case; the existing 2-class train
split is 68452:4741 = 14.4:1). Counter-evidence against over-engineering this:
in v1 the *minority* class did better — vest false alarms 14-34% vs helmet 100% —
so resolution, not frequency, is what broke. Ultralytics 8.4 has no sampler or
class-weight hook, so the mitigation is data-side and optional, after the merge:

```bash
cd ml/datasets/merged4
python - <<'EOF'
from pathlib import Path
out=[]
for lb in sorted(Path('labels/train').glob('*.txt')):
    im=f"./images/train/{lb.stem}.jpg"
    c={l.split()[0] for l in lb.read_text().split('\n') if l.strip()}
    out += [im] * (4 if '3' in c else 2 if '1' in c else 1)
Path('train_oversampled.txt').write_text('\n'.join(out))
EOF
# then point data.yaml at it:  train: train_oversampled.txt
```

`BaseDataset.get_img_files` reads a `.txt` list and its `sorted()` preserves
duplicates, so repeated paths do oversample. `settings.VIOLATION_CONFIDENCE_
THRESHOLD = 0.35` is already the runtime safety net for the thin `no_vest` class.

**Augmentation.** `scale: 0.9` is the single highest-leverage setting:
`RandomPerspective` draws `uniform(1-s, 1+s)`, so 0.9 maps a 60 px frontal helmet
across 6-114 px and covers the entire deployment range — v1's 0.5 bottomed out at
30 px, twice the size the camera ever produces. `mosaic: 1.0` is kept because
tiling 4 images into one canvas is itself a free small-object generator, but
`close_mosaic: 20` (up from 10) gives a longer clean tail so box regression
converges on real frame statistics rather than mosaic ones. `perspective: 0.001`
(2x v1) is the only augmentation that simulates frontal-to-high-mounted, which is
the actual domain gap. `degrees: 3.0` covers mast install tilt; v1's 10 deg is
unphysical for a fixed camera and inflates axis-aligned boxes on standing people.
`hsv_h` stays at 0.015 — hi-vis hue is the whole vest/no_vest signal. Zeroed:
`mixup` (ghosts a 12 px helmet into background), `copy_paste` (verified silent
no-op on box-only labels), `erasing` (classification-only). `multi_scale` stays
off: it peaks at 1.5x imgsz = 1440 px, which OOMs at this batch.

**Schedule.** 120 epochs, `patience: 25`, `cos_lr`, `warmup_epochs: 5.0` — the
long warmup because 45% of the network (the p2 neck and head) starts random.
`optimizer: SGD` is pinned deliberately: ultralytics 8.4's `auto` now resolves to
MuSGD above 10k iterations (this run has ~49k), which would silently change the
optimizer versus the v1 baseline. Measured throughput 40.1 img/s → ~11 min/epoch
of GPU compute on 26k images, so budget 20-30h wall clock with dataloading.

## The gate

**Do not judge this run by val mAP.** `merge_datasets.py` shuffles pooled frames
before splitting, so merged4's val split leaks the same way v1's did. The
acceptance test is the zero-annotation harness on real footage:

```bash
cd backend && PYTHONPATH=. .venv/bin/python ../ml/eval_compliant.py \
  ../ml/datasets/webcam_raw/frames --sweep
```

Every "missing" verdict there is a false alarm by construction. v1 baseline:
helmet 100%, vest 14-34%.

## Two loose ends this config cannot fix

- `ml/augment/pipeline.py` (Downscale 0.25-0.5, MotionBlur, Defocus,
  RandomShadow — precisely the H.264/compression realism this problem needs) is
  imported by nothing. Grep confirms zero callers; it has never touched the data.
  Wiring it into `merge_datasets.py` is the cheapest remaining gain.
- `stream.py`'s `HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX = 80` disables helmet checking
  below 80 px while the median worker in this footage is 58 px tall. A perfect
  model still reports nothing until that gate is lowered.

"""Zero-annotation evaluation on all-compliant footage.

Public construction footage is compliance theatre: every worker wears the PPE.
That is normally a problem (no violations to learn from) but it makes the
footage a free test set for the two failures that actually kill the product:

  * coverage    — how many workers does the pipeline even look at?
  * false alarm — of those, how many compliant workers get flagged?

No labels required. Every accusation on this footage is wrong by construction.
Two kinds of accusation are measured separately, because the 4-class model
exists precisely to replace the first with the second:

  FA-aus (absence)  no helmet box overlaps the head zone  -> "capacete ausente"
  FA-dir (direct)   a `head` / `no_vest` box overlaps the zone -> violation seen

A 2-class checkpoint only has FA-aus. A 4-class checkpoint has both, and the
comparison between the two columns is the whole point of the retrain.

Temporal smoothing is NOT replayed. On timelapse footage the real gap between
frames dwarfs SMOOTHING_TO_MISSING_S and tracks would not survive, so the
numbers here are per-frame. Smoothing only ever suppresses alerts, so this is
an upper bound on the alert rate and a lower bound on coverage.

Usage:
    cd backend
    PYTHONPATH=. .venv/bin/python ../ml/eval_compliant.py FRAMES_DIR
    PYTHONPATH=. .venv/bin/python ../ml/eval_compliant.py FRAMES_DIR --sweep
    PYTHONPATH=. .venv/bin/python ../ml/eval_compliant.py SITES_ROOT \
        --weights ../ml/runs/train/ppe-4c/weights/best.pt --sweep

FRAMES_DIR may be a flat directory of frames or a root holding several sites
(<root>/<site>/frames/*.jpg) — every site is reported on its own line plus an
aggregate, because an average hides a single catastrophic camera.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

IMG_GLOBS = ("*.jpg", "*.jpeg", "*.png")

# Person confidence used to build the "people actually present" denominator.
# Must be >= --candidate-conf or coverage is measured against a shrunk baseline.
BASELINE_CONF = 0.25

# Weights-file class name -> canonical key used by the backend pipeline.
# The backend speaks Portuguese for equipment and keeps the violation classes
# under their training names.
CANON: dict[str, str] = {
    "helmet": "capacete",
    "hardhat": "capacete",
    "hard_hat": "capacete",
    "hard-hat": "capacete",
    "capacete": "capacete",
    "vest": "colete",
    "safety_vest": "colete",
    "colete": "colete",
    "head": "head",
    "no_vest": "no_vest",
    "no-vest": "no_vest",
    "no_safety_vest": "no_vest",
}

# Violation class -> the equipment whose body zone it must overlap. Lets the
# violation classes reuse _evaluate_person's zone geometry and head-visibility
# rule instead of reimplementing them here.
VIOLATION_OF: dict[str, str] = {"head": "capacete", "no_vest": "colete"}

EQUIPMENT = ("capacete", "colete")

DEFAULT_GATES = "0.40:0.005,0.40:0.001,0.30:0.001,0.25:0.0005,0.15:0.0005"


def die(msg: str) -> "None":
    raise SystemExit(f"eval_compliant: {msg}")


def discover_sites(root: Path) -> list[tuple[str, list[str]]]:
    """[(site name, frame paths)]. Flat dir -> one site named after the dir."""
    if not root.exists():
        die(f"frames path does not exist: {root}")
    if not root.is_dir():
        die(f"frames path is not a directory: {root}")

    by_dir: dict[Path, list[str]] = {}
    for pattern in IMG_GLOBS:
        for p in root.rglob(pattern):
            by_dir.setdefault(p.parent, []).append(str(p))
    if not by_dir:
        die(f"no images ({'/'.join(IMG_GLOBS)}) anywhere under {root}")

    sites: list[tuple[str, list[str]]] = []
    for directory, files in sorted(by_dir.items()):
        parts = [p for p in directory.relative_to(root).parts if p != "frames"]
        sites.append(("/".join(parts) or root.name, sorted(files)))
    return sites


def parse_gates(spec: str) -> list[tuple[float, float]]:
    gates: list[tuple[float, float]] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        conf, _, area = chunk.partition(":")
        if not area:
            die(f"bad --gates entry {chunk!r}, expected CONF:AREA (e.g. 0.40:0.001)")
        try:
            gates.append((float(conf), float(area)))
        except ValueError:
            die(f"bad --gates entry {chunk!r}, expected two floats CONF:AREA")
    if not gates:
        die("--gates parsed to an empty list")
    return gates


def canonical_classes(names: dict[int, str]) -> dict[int, str]:
    """Weights' class index -> canonical key. Loud on anything unrecognised."""
    if not names:
        die("weights expose no class names")
    mapped: dict[int, str] = {}
    for idx, raw in names.items():
        key = CANON.get(str(raw).strip().lower().replace(" ", "_"))
        if key is None:
            die(
                f"class {idx} of the weights is {raw!r}, which maps to no known PPE "
                f"class. Known: {sorted(set(CANON))}"
            )
        mapped[int(idx)] = key
    return mapped


def detect_site(frames: list[str], person_model, detector, candidate_conf: float):
    """Detect once per frame; the gate sweep then replays these in memory."""
    import cv2

    cached = []
    unreadable = 0
    for f in frames:
        img = cv2.imread(f)
        if img is None:
            unreadable += 1
            continue
        h, w = img.shape[:2]
        r = person_model(f, classes=[0], conf=candidate_conf, verbose=False)[0]
        cands = [(float(b.conf[0]), tuple(int(v) for v in b.xyxy[0])) for b in r.boxes]
        cached.append((cands, detector.detect(img), float(h * w)))
    if not cached:
        die(f"every one of the {len(frames)} frames failed to decode")
    if unreadable:
        print(f"  warning: {unreadable}/{len(frames)} frames failed to decode",
              file=sys.stderr)
    return cached


def report(
    title: str,
    cached: list,
    gates: list[tuple[float, float]],
    equip: list[str],
    viol: list[str],
) -> None:
    from app.config import settings
    from app.models import Detection
    from app.stream import _evaluate_person

    baseline = sum(
        1 for cands, _, _ in cached for c, _ in cands if c >= BASELINE_CONF
    )
    print()
    print(f"=== {title} — {len(cached)} frames, "
          f"{baseline} pessoas (conf>={BASELINE_CONF}) ===")
    if baseline == 0:
        print("  NO PEOPLE DETECTED — coverage is undefined, numbers below are void")

    head = f"{'conf':>5} {'area':>7} | {'avaliadas':>9} {'cobert':>7} |"
    for c in equip:
        head += f" {'FA-aus ' + c:>16}"
    for v in viol:
        head += f" {'FA-dir ' + v:>16}"
    print(head)
    print("-" * len(head))

    for conf_th, area_th in gates:
        absent = {c: [0, 0] for c in equip}   # class -> [checkable, flagged]
        direct = {v: [0, 0] for v in viol}
        persons = 0
        for cands, ppe, area in cached:
            equip_dets = [d for d in ppe if d.class_name in equip]
            # Relabel each violation box as the equipment it contradicts, so
            # _evaluate_person applies the same zone + head-visibility rules.
            viol_dets = [
                Detection(VIOLATION_OF[d.class_name], d.confidence, d.bbox)
                for d in ppe
                if d.class_name in viol
            ]
            for conf, bb in cands:
                x1, y1, x2, y2 = bb
                bw, bh = max(1, x2 - x1), max(1, y2 - y1)
                if conf < conf_th:
                    continue
                if (bh / bw) < settings.PERSON_MIN_ASPECT_RATIO:
                    continue
                if (bw * bh) / area < area_th:
                    continue
                persons += 1

                ev, checkable = _evaluate_person(bb, equip_dets, set(equip))
                for cls in equip:
                    if cls in checkable:
                        absent[cls][0] += 1
                        absent[cls][1] += cls in ev.missing

                if viol:
                    zones = {VIOLATION_OF[v] for v in viol}
                    vev, vcheckable = _evaluate_person(bb, viol_dets, zones)
                    for v in viol:
                        if VIOLATION_OF[v] in vcheckable:
                            direct[v][0] += 1
                            direct[v][1] += VIOLATION_OF[v] in vev.present

        def fmt(pair: list[int]) -> str:
            n, bad = pair
            return f"{bad}/{n} {bad / n * 100:.0f}%" if n else "n/a"

        cov = f"{persons / baseline * 100:>6.0f}%" if baseline else "   n/a"
        line = f"{conf_th:>5} {area_th:>7} | {persons:>9} {cov} |"
        for c in equip:
            line += f" {fmt(absent[c]):>16}"
        for v in viol:
            line += f" {fmt(direct[v]):>16}"
        print(line)


def self_test() -> None:
    import tempfile

    assert parse_gates("0.4:0.001, 0.3:0.0005") == [(0.4, 0.001), (0.3, 0.0005)]
    assert canonical_classes({0: "helmet", 1: "Vest"}) == {0: "capacete", 1: "colete"}
    assert canonical_classes({2: "head", 3: "no_vest"}) == {2: "head", 3: "no_vest"}
    for bad in ("nope", "0.4", "x:y", ""):
        try:
            parse_gates(bad)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"parse_gates({bad!r}) should have exited")
    try:
        canonical_classes({0: "banana"})
    except SystemExit:
        pass
    else:
        raise AssertionError("canonical_classes should reject unknown classes")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            discover_sites(root)
        except SystemExit:
            pass
        else:
            raise AssertionError("discover_sites should reject an empty dir")

        (root / "siteA" / "frames").mkdir(parents=True)
        (root / "siteB" / "frames").mkdir(parents=True)
        (root / "siteA" / "frames" / "a.jpg").write_bytes(b"x")
        (root / "siteB" / "frames" / "b.png").write_bytes(b"x")
        assert [n for n, _ in discover_sites(root)] == ["siteA", "siteB"]

        flat = root / "siteA" / "frames"
        assert [n for n, _ in discover_sites(flat)] == ["frames"]
    print("eval_compliant self-test OK")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("frames", type=Path, nargs="?",
                   help="Flat frames dir, or a root of <site>/frames/")
    p.add_argument("--weights", type=Path, default=None,
                   help="PPE checkpoint to evaluate (default: settings.MODEL_PATH)")
    p.add_argument("--sweep", action="store_true", help="Vary the person gate")
    p.add_argument("--gates", default=DEFAULT_GATES,
                   help="Extra gates for --sweep as CONF:AREA,... "
                        "(production gate is always the first row)")
    p.add_argument("--candidate-conf", type=float, default=0.10,
                   help="Person confidence floor used to build the un-gated baseline")
    p.add_argument("--self-test", action="store_true",
                   help="Check the arg/discovery logic and exit (no model needed)")
    args = p.parse_args()

    if args.self_test:
        self_test()
        return
    if args.frames is None:
        p.error("frames directory is required")
    if args.candidate_conf > BASELINE_CONF:
        die(f"--candidate-conf {args.candidate_conf} > {BASELINE_CONF}: the coverage "
            f"denominator would be truncated and coverage silently inflated")

    extra_gates = parse_gates(args.gates) if args.sweep else []
    sites = discover_sites(args.frames)

    from ultralytics import YOLO

    from app.config import settings
    from app import detector as detector_mod
    from app.detector import SafetyDetector

    weights = Path(args.weights) if args.weights else Path(settings.MODEL_PATH)
    if not weights.is_file():
        die(f"weights not found: {weights.resolve()}")
    settings.MODEL_PATH = str(weights.resolve())

    # The backend hardcodes a 2-class index->name table. Rebuild it from the
    # checkpoint's own names so a 4-class model does not get its violation
    # classes silently dropped inside SafetyDetector.detect().
    mapping = canonical_classes(YOLO(str(weights)).names)
    detector_mod.EPI_CLASSES.clear()
    detector_mod.EPI_CLASSES.update(mapping)

    present = list(dict.fromkeys(mapping.values()))
    equip = [c for c in EQUIPMENT if c in present]
    viol = [v for v in VIOLATION_OF if v in present]
    if not equip and not viol:
        die(f"checkpoint has no evaluable class: {sorted(present)}")

    person_model = YOLO(settings.PERSON_MODEL_PATH)
    detector = SafetyDetector()
    detector.load_model()

    gates = [(settings.PERSON_CONFIDENCE_THRESHOLD, settings.PERSON_MIN_AREA_RATIO)]
    gates += [g for g in extra_gates if g not in gates]

    print(f"weights: {weights.resolve()}")
    print(f"classes: {mapping}")
    print(f"sites:   {len(sites)}")

    everything: list = []
    for name, frames in sites:
        cached = detect_site(frames, person_model, detector, args.candidate_conf)
        report(f"site {name}", cached, gates, equip, viol)
        everything.extend(cached)

    if len(sites) > 1:
        report("AGREGADO (todos os sites)", everything, gates, equip, viol)

    print()
    print("cobertura = pessoas que o pipeline avalia / pessoas realmente presentes")
    print("footage em conformidade: toda acusacao e' erro.")
    print("FA-aus = acusacao por AUSENCIA de EPI (inferencia).")
    if viol:
        print("FA-dir = acusacao por DETECCAO POSITIVA da violacao (head/no_vest).")
    else:
        print("FA-dir = n/a, checkpoint 2-classes nao detecta a violacao.")
    from app.stream import HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX

    print(f"capacete/head so' e' avaliado em pessoa >= "
          f"{HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX}px de altura (stream.py)")


if __name__ == "__main__":
    main()

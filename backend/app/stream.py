from __future__ import annotations

import logging
import threading
import time
from typing import Generator

import cv2
import numpy as np
from numpy.typing import NDArray

from collections import deque
from typing import Deque

from app.alerts import AlertManager
from app.config import settings
from app.detector import (
    ALL_CLASS_LABELS_PT,
    FACE_CLASS_KEY,
    EPI_ALERT_LABELS,
    EPI_LABELS_PT,
    VIOLATION_OF,
    Detection,
    SafetyDetector,
)
from app.observability import inference_latency, stream_fps, stream_online
from app.sources import StreamSource

logger = logging.getLogger(__name__)

TARGET_FPS = 25
FRAME_INTERVAL = 1.0 / TARGET_FPS

# Asymmetric temporal smoothing.
#   * Going TO "missing" is the more dangerous direction (false positive
#     "sem capacete" when the model momentarily drops the detection).
#     Demand stronger evidence (longer window).
#   * Going TO "present" is the safe direction. React quickly so the
#     person bbox flips back to green soon after a real detection
#     resumes.
SMOOTHING_TO_MISSING_S = 5.0
SMOOTHING_TO_PRESENT_S = 1.5
# Legacy alias used by older histories. Equal to the longer window.
SMOOTHING_WINDOW_S = SMOOTHING_TO_MISSING_S

# A person's helmet status is only checked when their head zone is
# plausibly visible in frame. Bboxes touching the top edge are assumed
# clipped (camera angle, occlusion) and skip the helmet check entirely
# rather than wrongly flag the person as "sem capacete".
HEAD_VISIBLE_TOP_MARGIN_PX = 6
HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX = 80

# How much overlap is required between a PPE bbox and a person's head/torso
# zone for it to count as "worn by that person". Low because PPE bboxes are
# small and partial overlap (e.g. helmet edge inside head zone) is normal.
PPE_PERSON_MIN_OVERLAP = 0.10

# Fraction of a person's height treated as the head. Used both to decide
# whether a helmet belongs to that person and to anonymise the review image.
HEAD_ZONE_FRACTION = 0.30

# Where the face sits INSIDE the head zone, as fractions of that zone.
# Anonymisation and evidence pull in opposite directions: the helmet sits on
# the crown, the face just below it, and blurring the whole zone hides the very
# thing the reviewer has to judge. The zone is 30% of a person's height, which
# reaches the chest, so the band must also STOP — an open-ended band blurred
# the torso and left the face exposed above it.
FACE_BAND_START = 0.12
FACE_BAND_END = 0.55

# Per-track tuning
TRACK_IOU_THRESHOLD = 0.30
TRACK_STALE_S = 1.5
# A class is considered "missing" for a track only if it was missing in this
# fraction of recent observations within SMOOTHING_WINDOW_S. Keeps bbox color
# stable across single-frame mis-detections.
TRACK_MISSING_FRACTION = 0.70
TRACK_MIN_SAMPLES = 8

# Throttle alerts: regardless of which classes change, never emit two alerts
# within this many seconds for the same camera. Stops the per-second alert
# spam when the model flickers between cap-only and cap+colete missing.
ALERT_MIN_INTERVAL_S = 8.0

# Maximum gap between two positive detections of the same class that still
# counts as a continuous "present" streak. A gap longer than this resets
# the streak so the worker has to re-establish presence over the full
# SMOOTHING_WINDOW_S before the bbox flips back to green.
CLASS_STREAK_RESET_GAP_S = 2.5


class PersonEval:
    __slots__ = ("bbox", "present", "missing", "matched", "violated")

    def __init__(
        self,
        bbox: tuple[int, int, int, int],
        present: set[str],
        missing: set[str],
        matched: list[Detection],
        violated: set[str] | None = None,
    ) -> None:
        self.bbox = bbox
        self.present = present
        self.missing = missing
        self.matched = matched
        # EPI keys with POSITIVE evidence of violation (a bare-head / no-vest
        # box overlapping this person), as opposed to merely undetected PPE.
        self.violated = violated if violated is not None else set()


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    iw = max(0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = max(1, (ax2 - ax1) * (ay2 - ay1)) + max(1, (bx2 - bx1) * (by2 - by1)) - inter
    return inter / union


def _bbox_overlap_ratio(
    inner: tuple[int, int, int, int], zone: tuple[int, int, int, int]
) -> float:
    ix1, iy1, ix2, iy2 = inner
    zx1, zy1, zx2, zy2 = zone
    inter_w = max(0, min(ix2, zx2) - max(ix1, zx1))
    inter_h = max(0, min(iy2, zy2) - max(iy1, zy1))
    inter = inter_w * inter_h
    if inter == 0:
        return 0.0
    inner_area = max(1, (ix2 - ix1) * (iy2 - iy1))
    return inter / inner_area


def _head_zone(person_bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Top slice of a person box: where a helmet sits, and where a face is.

    Shared by the helmet-association check and by anonymisation so the two can
    never drift apart."""
    px1, py1, px2, py2 = person_bbox
    ph = py2 - py1
    return (px1, py1, px2, py1 + max(1, int(ph * HEAD_ZONE_FRACTION)))


def _face_band(person_bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """The part of the head zone to anonymise: below the helmet, above the neck.

    Blurring the whole head zone also blurs the hard hat, which is the evidence
    the alert exists to show. Starting at FACE_BAND_START keeps the crown and
    brim sharp while covering the face."""
    x1, y1, x2, y2 = _head_zone(person_bbox)
    zone_h = y2 - y1
    top = y1 + int(zone_h * FACE_BAND_START)
    bottom = y1 + int(zone_h * FACE_BAND_END)
    top = min(top, y2 - 1)
    return (x1, top, x2, max(bottom, top + 1))


def _bump_streak(tr: dict, last_key: str, start_key: str, cls: str, now: float) -> None:
    """Extend (or restart, after a gap) a per-class evidence streak on a track."""
    last_map = tr.setdefault(last_key, {})
    start_map = tr.setdefault(start_key, {})
    last = last_map.get(cls)
    if last is None or (now - last) > CLASS_STREAK_RESET_GAP_S:
        start_map[cls] = now
    last_map[cls] = now


def _absence_implies_violation(detector: SafetyDetector) -> bool:
    """Whether "PPE not detected" alone counts as a violation.

    "auto" resolves to False as soon as the loaded weights can detect the
    violation directly — absence-inference is what produced a 100% helmet
    false alarm rate on compliant CCTV footage (ml/eval_compliant.py)."""
    mode = settings.ABSENCE_IMPLIES_VIOLATION.strip().lower()
    if mode == "on":
        return True
    if mode == "off":
        return False
    return not bool(getattr(detector, "has_violation_classes", False))


def _absence_classes(detector: SafetyDetector, active: set[str]) -> set[str]:
    """Which EPI keys still fall back to absence-inference, decided per class.

    Coarse on/off would be wrong: the 4-class weights detect a bare head well
    (recall 0.80) but sem_colete not at all (recall 0.00 on 20 training boxes).
    Retiring absence-inference for every class at once would leave vests with
    no detector and no fallback, silently ending vest enforcement."""
    mode = settings.ABSENCE_IMPLIES_VIOLATION.strip().lower()
    if mode == "on":
        return set(active)
    if mode == "off":
        return set()
    covered = getattr(detector, "trusted_violation_equipment", None) or set()
    return {cls for cls in active if cls not in covered}


def _evaluate_person(
    person_bbox: tuple[int, int, int, int],
    ppe_dets: list[Detection],
    active: set[str],
    absence_implies_violation: bool | set[str] = True,
) -> tuple["PersonEval", set[str]]:
    """Returns (eval, checkable_classes). Classes not in checkable should be
    treated as undecidable for this person — typically because the body part
    needed to assess them is not visible in frame.

    A violation is preferably established by POSITIVE evidence: a
    cabeca_descoberta / sem_colete box overlapping the matching body zone.
    Absence-inference ("no helmet box => no helmet") is the fallback. Pass True
    to apply it to every active class, False to none, or the explicit set of
    classes that still need it (see _absence_classes)."""
    if absence_implies_violation is True:
        absence = set(active)
    elif absence_implies_violation is False:
        absence = set()
    else:
        absence = set(absence_implies_violation)

    px1, py1, px2, py2 = person_bbox
    ph = py2 - py1
    head_visible = (
        py1 > HEAD_VISIBLE_TOP_MARGIN_PX
        and ph >= HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX
    )
    head_zone = _head_zone(person_bbox)
    torso_zone = (px1, py1 + int(ph * 0.20), px2, py1 + int(ph * 0.70))

    checkable = set(active)
    if not head_visible and "capacete" in absence:
        # Guessing from absence needs the head to be plausibly visible.
        # Positive evidence needs no such guard: seeing a bare head IS the
        # proof that the head is visible.
        checkable.discard("capacete")

    present: set[str] = set()
    violated: set[str] = set()
    matched: list[Detection] = []
    for d in ppe_dets:
        violates = VIOLATION_OF.get(d.class_name)
        cls = violates or d.class_name
        # A violation that was SEEN is decidable by definition; PPE presence
        # is only assessed for classes this person's visible body allows.
        if cls not in (active if violates else checkable):
            continue
        zone = head_zone if cls == "capacete" else torso_zone
        if _bbox_overlap_ratio(d.bbox, zone) < PPE_PERSON_MIN_OVERLAP:
            continue
        if violates:
            violated.add(cls)
        else:
            present.add(cls)
            matched.append(d)

    missing = set(violated)
    missing |= (checkable & absence) - present
    return PersonEval(person_bbox, present, missing, matched, violated), checkable


def _annotate_per_person(
    frame: NDArray[np.uint8],
    person_evals: list["PersonEval"],
    all_ppe: list[Detection],
    faces: list[Detection],
) -> NDArray[np.uint8]:
    GREEN = (100, 220, 100)
    RED = (40, 40, 230)
    GRAY = (160, 160, 160)
    LABEL_BG_GREEN = (60, 160, 60)
    LABEL_BG_RED = (30, 30, 180)
    LABEL_BG_GRAY = (90, 90, 90)

    out = frame.copy()

    # Only draw internal PPE bboxes for persons that have at least one
    # missing class — when everything is OK the inner labels are visual
    # noise; outer "OK" badge is enough.
    show_internal_for_ids = {
        id(d)
        for ev in person_evals
        if ev.missing
        for d in ev.matched
    }
    for d in all_ppe:
        if id(d) not in show_internal_for_ids:
            continue
        x1, y1, x2, y2 = d.bbox
        cv2.rectangle(out, (x1, y1), (x2, y2), GREEN, 2)
        label = EPI_LABELS_PT.get(d.class_name, d.class_name)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(out, (x1, y1 - th - 8), (x1 + tw + 6, y1), LABEL_BG_GREEN, -1)
        cv2.putText(out, label, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    for ev in person_evals:
        x1, y1, x2, y2 = ev.bbox
        if ev.missing:
            color, bg = RED, LABEL_BG_RED
            missing_lbls = ", ".join(sorted(EPI_LABELS_PT.get(k, k) for k in ev.missing))
            label = f"Sem {missing_lbls}"
        elif ev.present:
            color, bg = GREEN, LABEL_BG_GREEN
            label = "OK"
        else:
            # Track is too young to commit a status — neutral gray.
            color, bg = GRAY, LABEL_BG_GRAY
            label = "Avaliando"
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(out, (x1, y1 - th - 8), (x1 + tw + 6, y1), bg, -1)
        cv2.putText(out, label, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    return out


class StreamProcessor:
    def __init__(
        self,
        source: StreamSource,
        detector: SafetyDetector,
        alert_manager: AlertManager,
        owns_source: bool = True,
        camera_id: str | None = None,
    ) -> None:
        self._source = source
        self._detector = detector
        self._alert_manager = alert_manager
        self._owns_source = owns_source
        self._camera_id = camera_id or "unknown"
        self._stop_event = threading.Event()
        self._stop_event.set()  # Start in stopped state
        self._epoch: int = 0
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._current_jpeg: bytes = b""
        self._fps: float = 0.0
        self._start_time: float = 0.0
        self._active_epis: set[str] = set()
        self._epi_lock = threading.Lock()
        self._last_missing_set: frozenset[str] = frozenset()
        # Per-class history of (timestamp, detection). Used for temporal smoothing.
        self._detection_history: dict[str, Deque[tuple[float, Detection]]] = {}
        # Person presence smoothed window (timestamps when any detection / face was seen)
        self._person_seen_history: Deque[float] = deque()
        # Per-person tracks: list of {bbox, last_seen, history: deque[(t, frozenset[missing])]}
        self._tracks: list[dict] = []
        # Last alert wall-clock time (monotonic) for global throttling
        self._last_alert_at: float = 0.0
        # Per-camera color palette override. None = use global default in detector.
        self._color_palettes: dict[str, list[tuple[tuple[int, int, int], tuple[int, int, int]]]] | None = None
        self._palette_lock = threading.Lock()

    @property
    def active_epis(self) -> set[str]:
        with self._epi_lock:
            return self._active_epis.copy()

    def set_active_epis(self, epis: set[str]) -> None:
        # Only real EPIs are selectable. Violation classes are evidence, and
        # main.py derives its valid-key set from EPI_CLASSES, which has them.
        with self._epi_lock:
            self._active_epis = {e for e in epis if e in EPI_LABELS_PT}

    @property
    def color_palettes(self) -> dict[str, list[tuple[tuple[int, int, int], tuple[int, int, int]]]] | None:
        with self._palette_lock:
            return None if self._color_palettes is None else {
                k: list(v) for k, v in self._color_palettes.items()
            }

    def set_color_palettes(
        self,
        palettes: dict[str, list[tuple[tuple[int, int, int], tuple[int, int, int]]]] | None,
    ) -> None:
        with self._palette_lock:
            self._color_palettes = (
                None
                if palettes is None
                else {k: list(v) for k, v in palettes.items()}
            )

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set()

    @property
    def fps(self) -> float:
        with self._lock:
            return self._fps

    @property
    def uptime(self) -> float:
        with self._lock:
            start = self._start_time
        if start == 0.0:
            return 0.0
        return time.monotonic() - start

    def start(self) -> None:
        if self.is_running:
            logger.warning("Stream processor already running")
            return

        if not self._detector.is_loaded:
            self._detector.load_model()

        self._epoch += 1
        if self._owns_source:
            try:
                self._source.start()
            except Exception:
                logger.exception("Failed to start source")
                raise
        self._stop_event.clear()
        with self._lock:
            self._start_time = time.monotonic()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("Stream processor started (epoch=%d)", self._epoch)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._owns_source:
            self._source.stop()
        self._alert_manager.reset_session()
        with self._lock:
            self._current_jpeg = b""
            self._start_time = 0.0
            self._fps = 0.0
        logger.info("Stream processor stopped")

    def get_jpeg_frame(self) -> bytes:
        with self._lock:
            return self._current_jpeg

    def generate_mjpeg(self) -> Generator[bytes, None, None]:
        epoch = self._epoch
        while not self._stop_event.is_set() and epoch == self._epoch:
            frame = self.get_jpeg_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            # Wait with Event so stop() wakes us immediately
            self._stop_event.wait(0.03)

    def _process_loop(self) -> None:
        frame_count = 0
        fps_timer = time.monotonic()

        while not self._stop_event.is_set():
            loop_start = time.monotonic()

            frame = self._source.get_frame()
            if frame is None:
                stream_online.labels(camera_id=self._camera_id).set(0)
                self._stop_event.wait(0.01)
                continue
            stream_online.labels(camera_id=self._camera_id).set(1)

            inf_start = time.monotonic()
            with self._palette_lock:
                palettes = (
                    None if self._color_palettes is None else {
                        k: list(v) for k, v in self._color_palettes.items()
                    }
                )
            detections = self._detector.detect(frame, color_palettes=palettes)
            persons = self._detector.detect_persons(frame)
            inference_latency.observe(time.monotonic() - inf_start)

            with self._epi_lock:
                active = self._active_epis.copy()
            visible_faces = [d for d in detections if d.class_name == FACE_CLASS_KEY]
            # Includes the violation classes — they are the positive evidence.
            ppe_dets = [d for d in detections if d.class_name in ALL_CLASS_LABELS_PT]

            now = time.monotonic()
            absence_ok = _absence_classes(self._detector, active)  # per-class set

            # Per-frame raw evaluation per detected person.
            raw_evals: list[PersonEval] = []
            raw_checkable: list[set[str]] = []
            for pbox in persons:
                ev, ck = _evaluate_person(pbox, ppe_dets, active, absence_ok)
                raw_evals.append(ev)
                raw_checkable.append(ck)

            # Update tracks: match raw_evals against existing tracks by IoU.
            matched_track_ids: set[int] = set()
            for idx, ev in enumerate(raw_evals):
                checkable_now = raw_checkable[idx]
                best_tr = None
                best_iou = TRACK_IOU_THRESHOLD
                for tr in self._tracks:
                    if id(tr) in matched_track_ids:
                        continue
                    iou = _iou(tr["bbox"], ev.bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_tr = tr
                if best_tr is not None:
                    matched_track_ids.add(id(best_tr))
                    best_tr["bbox"] = ev.bbox
                    best_tr["last_seen"] = now
                    best_tr["last_matched_dets"] = ev.matched
                    best_tr["last_checkable"] = checkable_now
                    last_det_per_cls = best_tr.setdefault("last_det_per_cls", {})
                    for d in ev.matched:
                        last_det_per_cls[d.class_name] = d
                    for cls in active:
                        if cls in ev.present:
                            _bump_streak(
                                best_tr, "last_class_seen", "class_streak_start", cls, now
                            )
                        if cls in ev.violated:
                            _bump_streak(
                                best_tr,
                                "last_violation_seen",
                                "violation_streak_start",
                                cls,
                                now,
                            )
                else:
                    # No status snapshot. New tracks start fully UNDEFINED
                    # for every active class. A status only commits after
                    # SMOOTHING_WINDOW_S of consistent evidence.
                    new_tr = {
                        "bbox": ev.bbox,
                        "first_seen": now,
                        "last_seen": now,
                        "last_class_seen": {cls: now for cls in ev.present},
                        "class_streak_start": {cls: now for cls in ev.present},
                        "last_violation_seen": {cls: now for cls in ev.violated},
                        "violation_streak_start": {cls: now for cls in ev.violated},
                        "class_status": {},  # undefined
                        "last_matched_dets": ev.matched,
                        "last_det_per_cls": {d.class_name: d for d in ev.matched},
                        "last_checkable": checkable_now,
                        # was_compliant=True default so the first commit
                        # to "missing" cleanly fires exactly one alert via
                        # the OK -> NOT-OK edge logic below.
                        "was_compliant": True,
                    }
                    self._tracks.append(new_tr)

            # Drop stale tracks
            self._tracks = [
                tr for tr in self._tracks if (now - tr["last_seen"]) <= TRACK_STALE_S
            ]

            # Symmetric smoothing per track per class. Status only commits
            # after SMOOTHING_WINDOW_S of consistent evidence, in either
            # direction. Internal PPE bboxes drawn for the person follow
            # the same smoothed status so they cannot disagree with the
            # outer person bbox color.
            person_evals: list[PersonEval] = []
            triggered_alerts: list[
                tuple[set[str], list[Detection], tuple[int, int, int, int]]
            ] = []
            for tr in self._tracks:
                age = now - tr["first_seen"]
                cstatus: dict[str, str] = tr.setdefault("class_status", {})
                checkable_now: set[str] = tr.get("last_checkable", set(active))

                for cls in active:
                    last_t = tr["last_class_seen"].get(cls)
                    streak_start = tr["class_streak_start"].get(cls)
                    vio_t = tr.get("last_violation_seen", {}).get(cls)
                    vio_start = tr.get("violation_streak_start", {}).get(cls)
                    current = cstatus.get(cls)

                    present_committed = (
                        streak_start is not None
                        and last_t is not None
                        and (now - last_t) <= CLASS_STREAK_RESET_GAP_S
                        and (now - streak_start) >= SMOOTHING_TO_PRESENT_S
                    )
                    # Positive evidence of violation, held for the same
                    # cautious window absence-inference used to demand.
                    violation_committed = (
                        vio_start is not None
                        and vio_t is not None
                        and (now - vio_t) <= CLASS_STREAK_RESET_GAP_S
                        and (now - vio_start) >= SMOOTHING_TO_MISSING_S
                    )

                    if current == "present":
                        # Contradictory evidence (helmet AND bare head boxes on
                        # the same person) resolves toward the violation.
                        if violation_committed or (
                            cls in absence_ok
                            and (last_t is None or (now - last_t) >= SMOOTHING_TO_MISSING_S)
                        ):
                            cstatus[cls] = "missing"
                    elif current == "missing":
                        if present_committed and not violation_committed:
                            cstatus[cls] = "present"
                    else:
                        # Undefined first commit:
                        #   * "missing" needs a violation streak (or, in legacy
                        #     absence mode, TO_MISSING_S without any sighting)
                        #   * "present" earns its way in with TO_PRESENT_S of streak
                        if violation_committed or (
                            cls in absence_ok
                            and last_t is None
                            and age >= SMOOTHING_TO_MISSING_S
                        ):
                            cstatus[cls] = "missing"
                        elif present_committed:
                            cstatus[cls] = "present"

                missing = {
                    cls for cls in active
                    if cstatus.get(cls) == "missing" and cls in checkable_now
                }
                present = {cls for cls in active if cstatus.get(cls) == "present"}
                # Internal bboxes drawn = smoothed-present detections only.
                last_det = tr.get("last_det_per_cls", {})
                smoothed_matched = [last_det[c] for c in present if c in last_det]

                person_evals.append(
                    PersonEval(
                        bbox=tr["bbox"],
                        present=present,
                        missing=missing,
                        matched=smoothed_matched,
                    )
                )

                is_compliant_now = not missing
                was_compliant = tr.get("was_compliant", True)
                if was_compliant and not is_compliant_now:
                    # Carry the offender's box so the review image can be
                    # cropped to them: on a wide frame the violation is a
                    # few percent of the pixels, and the reviewer is
                    # deciding on a phone.
                    triggered_alerts.append(
                        (set(missing), list(smoothed_matched), tuple(tr["bbox"]))
                    )
                tr["was_compliant"] = is_compliant_now

            scene_missing: set[str] = set()
            for ev in person_evals:
                scene_missing |= ev.missing

            cutoff = now - SMOOTHING_WINDOW_S
            if persons or ppe_dets or visible_faces:
                self._person_seen_history.append(now)
            while self._person_seen_history and self._person_seen_history[0] < cutoff:
                self._person_seen_history.popleft()

            # Build the annotated frame up-front so we can persist both raw
            # and annotated versions when an alert fires below.
            annotated = _annotate_per_person(
                frame, person_evals, ppe_dets, visible_faces
            )

            for miss_set, matched_dets, offender_bbox in triggered_alerts:
                missing_labels = sorted(EPI_LABELS_PT.get(k, k) for k in miss_set)
                labels = ", ".join(missing_labels)
                rep_conf = max(
                    (d.confidence for d in (matched_dets or ppe_dets)), default=0.5
                )
                # Snapshot every detection currently visible in the scene as
                # a JSON-friendly record. RetrainingExporter materialises
                # YOLO labels from these later.
                bbox_records = [
                    {
                        "class_name": d.class_name,
                        "bbox": [int(v) for v in d.bbox],
                        "confidence": float(d.confidence),
                    }
                    for d in ppe_dets
                ]
                self._alert_manager.add_alert(
                    f"{labels} ausente(s)",
                    rep_conf,
                    annotated,
                    missing_epis=missing_labels,
                    raw_frame=frame,
                    detected_bboxes=bbox_records,
                    # Anonymise by the head zone of every detected person, not
                    # only by detected faces. The Haar cascade is frontal-only:
                    # measured on real alert frames it found 0 faces at every
                    # minSize, because workers are seen from the side or above
                    # with the hard hat shading the face. Relying on it means
                    # shipping an unblurred face. Over-blurring is harmless;
                    # under-blurring is a privacy leak.
                    face_bboxes=(
                        [d.bbox for d in visible_faces]
                        + [_face_band(ev.bbox) for ev in person_evals]
                    ),
                    focus_bbox=offender_bbox,
                )
                self._last_alert_at = now
            self._last_missing_set = frozenset(scene_missing)

            if person_evals:
                compliant_count = sum(1 for ev in person_evals if not ev.missing)
                is_compliant = compliant_count == len(person_evals)
            else:
                is_compliant = True

            self._alert_manager.record_frame(compliant=is_compliant)

            success, buffer = cv2.imencode(".jpg", annotated)
            if success:
                jpeg_bytes: bytes = buffer.tobytes()
                with self._lock:
                    self._current_jpeg = jpeg_bytes

            frame_count += 1
            elapsed = time.monotonic() - fps_timer
            if elapsed >= 1.0:
                fps_value = round(frame_count / elapsed, 1)
                with self._lock:
                    self._fps = fps_value
                stream_fps.labels(camera_id=self._camera_id).set(fps_value)
                frame_count = 0
                fps_timer = time.monotonic()

            # FPS throttling: sleep remaining time to hit TARGET_FPS
            processing_time = time.monotonic() - loop_start
            sleep_time = FRAME_INTERVAL - processing_time
            if sleep_time > 0:
                self._stop_event.wait(sleep_time)

        logger.debug("Process loop exited")

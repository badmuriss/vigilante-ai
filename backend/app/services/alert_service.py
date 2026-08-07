"""Per-camera alert service: persists alerts to DB + frames to blob store.

Replaces the in-memory `AlertManager` for the new flow. Frame counters
(used for compliance rate during a session) remain in memory because
they tick on every frame and would crush the DB if persisted directly.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Callable
from uuid import uuid4

import cv2
import numpy as np
from numpy.typing import NDArray

from app.config import settings
from app.db.base import session_scope
from app.observability import alerts_total
from app.repositories import AlertRepository
from app.storage import BlobStore

logger = logging.getLogger(__name__)


class AlertService:
    """Replacement for AlertManager — persists to Postgres + filesystem."""

    def __init__(
        self,
        camera_id: str,
        blob_store: BlobStore,
        on_created: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._camera_id = camera_id
        self._blob_store = blob_store
        # Fired after a new (pending) alert is persisted. Used to push the
        # review notification to WhatsApp operators. Never allowed to break
        # the stream loop.
        self._on_created = on_created
        self._cooldowns: dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._session_start: datetime = datetime.utcnow()
        self._total_frames: int = 0
        self._compliant_frames: int = 0

    # --- write path ---

    def add_alert(
        self,
        violation_type: str,
        confidence: float,
        frame: NDArray[np.uint8],
        missing_epis: list[str] | None = None,
        raw_frame: NDArray[np.uint8] | None = None,
        detected_bboxes: list[dict[str, Any]] | None = None,
        face_bboxes: list[tuple[int, int, int, int]] | None = None,
        focus_bbox: tuple[int, int, int, int] | None = None,
    ) -> dict[str, Any] | None:
        if self._is_on_cooldown(violation_type):
            return None

        # Suppress duplicates while a reviewer hasn't yet decided on the prior
        # alert for this (camera, violation_type). Otherwise the same persistent
        # violation re-spawns every cooldown window and the pending queue
        # never drains for the supervisor.
        try:
            with session_scope() as session:
                if AlertRepository(session).has_unreviewed(
                    self._camera_id, violation_type
                ):
                    with self._lock:
                        self._cooldowns[violation_type] = datetime.utcnow()
                    return None
        except Exception:
            logger.exception(
                "has_unreviewed check failed for camera %s; falling through",
                self._camera_id,
            )

        alert_id = str(uuid4())
        quality = settings.ALERT_JPEG_QUALITY
        # Anonymise the human-facing artefacts (thumbnail + annotated frame).
        # Every alert passes through here, so panel and WhatsApp are covered at
        # once and no future caller can leak an unblurred face by omission.
        review_frame = _blur_faces(frame, face_bboxes)
        # Crop to the offender, for BOTH the thumbnail and the full artefact.
        # On a wide frame the violation is a few percent of the pixels and the
        # reviewer is deciding on a phone. Blur runs first, so the crop
        # inherits it and cannot expose a face the crop happens to include.
        # The raw artefact below stays uncropped: retraining wants the whole
        # scene, including the background the detector has to reject.
        review_frame = _crop_to_focus(review_frame, focus_bbox)
        thumb_jpeg = _encode_jpeg(review_frame, width=160, quality=quality)
        # Annotated frame at native resolution for high-quality admin review.
        full_jpeg = _encode_jpeg(review_frame, width=None, quality=quality)
        # Raw (un-annotated) frame at native resolution for retraining export.
        # Deliberately NOT blurred: the hardhat sits on the head, adjacent to
        # the face region, so blurring there destroys exactly the signal YOLO
        # must learn for hardhat/no_hardhat. Privacy on the raw artefact is
        # handled by access control + short retention, not by pixels.
        raw_jpeg = (
            _encode_jpeg(raw_frame, width=None, quality=quality)
            if raw_frame is not None
            else b""
        )

        thumb_path = (
            self._blob_store.save_jpeg(
                camera_id=self._camera_id,
                alert_id=alert_id,
                kind="thumb",
                data=thumb_jpeg,
            )
            if thumb_jpeg
            else None
        )
        frame_path = (
            self._blob_store.save_jpeg(
                camera_id=self._camera_id,
                alert_id=alert_id,
                kind="frame",
                data=full_jpeg,
            )
            if full_jpeg
            else None
        )
        raw_path = (
            self._blob_store.save_jpeg(
                camera_id=self._camera_id,
                alert_id=alert_id,
                kind="raw",
                data=raw_jpeg,
            )
            if raw_jpeg
            else None
        )

        try:
            with session_scope() as session:
                repo = AlertRepository(session)
                repo.create(
                    camera_id=self._camera_id,
                    violation_type=violation_type,
                    confidence=confidence,
                    missing_epis=missing_epis or [],
                    frame_path=frame_path,
                    thumbnail_path=thumb_path,
                    frame_raw_path=raw_path,
                    detected_bboxes=detected_bboxes or [],
                    alert_id=alert_id,
                )
                session.commit()
        except Exception:
            logger.exception("Failed to persist alert for camera %s", self._camera_id)
            # Roll back blobs to avoid orphans
            for p in (thumb_path, frame_path, raw_path):
                if p is not None:
                    self._blob_store.delete(p)
            return None

        with self._lock:
            self._cooldowns[violation_type] = datetime.utcnow()
        alerts_total.labels(
            camera_id=self._camera_id, violation_type=violation_type
        ).inc()
        result = {
            "id": alert_id,
            "camera_id": self._camera_id,
            "violation_type": violation_type,
            "confidence": confidence,
            "missing_epis": missing_epis or [],
            "frame_path": frame_path,
            "thumbnail_path": thumb_path,
        }
        if self._on_created is not None:
            try:
                self._on_created(result)
            except Exception:
                logger.exception(
                    "on_created hook failed for alert %s", alert_id
                )
        return result

    # --- in-memory frame counters (per-session compliance) ---

    def record_frame(self, *, compliant: bool) -> None:
        with self._lock:
            self._total_frames += 1
            if compliant:
                self._compliant_frames += 1

    def reset_session(self) -> None:
        with self._lock:
            self._cooldowns.clear()
            self._total_frames = 0
            self._compliant_frames = 0
            self._session_start = datetime.utcnow()

    def session_compliance(self) -> dict[str, Any]:
        with self._lock:
            total = self._total_frames
            compliant = self._compliant_frames
            started = self._session_start
        rate = (compliant / total * 100.0) if total > 0 else 100.0
        duration = (datetime.utcnow() - started).total_seconds()
        return {
            "total_frames": total,
            "compliant_frames": compliant,
            "compliance_rate": round(rate, 1),
            "session_duration_seconds": round(duration, 1),
        }

    # --- internal ---

    def _is_on_cooldown(self, violation_type: str) -> bool:
        with self._lock:
            last = self._cooldowns.get(violation_type)
        if last is None:
            return False
        return datetime.utcnow() - last < timedelta(seconds=settings.ALERT_COOLDOWN_SECONDS)


# How much of the offender's own size to keep around them, so the crop reads as
# a scene and not a mugshot. 0.6 => 60% of the box width added on each side.
FOCUS_PAD_RATIO = 0.6
# Never return a crop narrower than this fraction of the frame: on a close-up
# the box already fills most of the image and a tight crop just looks broken.
FOCUS_MIN_FRAME_RATIO = 0.35


def _crop_to_focus(
    frame: NDArray[np.uint8], bbox: tuple[int, int, int, int] | None
) -> NDArray[np.uint8]:
    """Crop around `bbox` with padding, so the review image shows the violation.

    Aspect is deliberately NOT preserved. A standing worker fills most of a
    landscape frame's height, so an aspect-correct crop containing them would
    have to be wider than the frame itself — the crop would always bail out and
    nothing would ever zoom. Cropping to the subject yields a portrait image,
    which is the better shape for the phone the reviewer is holding anyway.

    Returns the frame untouched when there is no box or the box is degenerate.
    """
    if bbox is None:
        return frame
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (int(v) for v in bbox)
    x1, x2 = sorted((max(0, x1), min(width, x2)))
    y1, y2 = sorted((max(0, y1), min(height, y2)))
    bw, bh = x2 - x1, y2 - y1
    if bw <= 0 or bh <= 0:
        return frame

    want_w = min(width, max(bw * (1 + 2 * FOCUS_PAD_RATIO),
                            width * FOCUS_MIN_FRAME_RATIO))
    want_h = min(height, bh * (1 + 2 * FOCUS_PAD_RATIO))
    # Nothing to gain if the padded box already spans the frame both ways.
    if want_w >= width and want_h >= height:
        return frame

    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    left = int(max(0, min(width - want_w, cx - want_w / 2)))
    top = int(max(0, min(height - want_h, cy - want_h / 2)))
    crop = frame[top:top + int(want_h), left:left + int(want_w)]
    return crop if crop.size else frame


def _blur_faces(
    frame: NDArray[np.uint8], boxes: list[tuple[int, int, int, int]] | None
) -> NDArray[np.uint8]:
    """Return a **copy** of `frame` with every face box Gaussian-blurred.

    The kernel scales with the box so a distant (small) face is hidden as
    thoroughly as a close one. Boxes are clipped to the frame, and degenerate
    boxes (zero/negative width or height after clipping) are skipped instead
    of raising.
    """
    out: NDArray[np.uint8] = frame.copy()
    if not boxes:
        return out
    height, width = out.shape[:2]
    for x1, y1, x2, y2 in boxes:
        left = max(0, min(int(x1), width))
        top = max(0, min(int(y1), height))
        right = max(0, min(int(x2), width))
        bottom = max(0, min(int(y2), height))
        if right <= left or bottom <= top:
            continue
        region = out[top:bottom, left:right]
        # Kernel ~1/3 of the smaller side, forced odd and >= 3 (cv2 requires
        # positive odd ksize).
        ksize = max(3, (min(right - left, bottom - top) // 3) | 1)
        out[top:bottom, left:right] = cv2.GaussianBlur(region, (ksize, ksize), 0)
    return out


def _encode_jpeg(
    frame: NDArray[np.uint8], width: int | None, quality: int = 95
) -> bytes:
    """Encode `frame` to JPEG bytes. `width=None` keeps native resolution."""
    if width is None:
        resized = frame
    else:
        src_h, src_w = frame.shape[:2]
        target_w = min(width, src_w)
        target_h = max(1, int(src_h * (target_w / src_w)))
        resized = cv2.resize(frame, (target_w, target_h))
    success, buffer = cv2.imencode(
        ".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    )
    if not success:
        return b""
    return bytes(buffer.tobytes())

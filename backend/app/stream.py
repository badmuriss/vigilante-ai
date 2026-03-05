from __future__ import annotations

import logging
import threading
import time
from typing import Generator

import cv2
import numpy as np
from numpy.typing import NDArray

from app.alerts import AlertManager
from app.camera import CameraManager
from app.detector import VIOLATION_CLASSES, SafetyDetector

logger = logging.getLogger(__name__)


class StreamProcessor:
    def __init__(
        self,
        camera: CameraManager,
        detector: SafetyDetector,
        alert_manager: AlertManager,
    ) -> None:
        self._camera = camera
        self._detector = detector
        self._alert_manager = alert_manager
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._current_jpeg: bytes = b""
        self._fps: float = 0.0
        self._start_time: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def uptime(self) -> float:
        if self._start_time == 0.0:
            return 0.0
        return time.monotonic() - self._start_time

    def start(self) -> None:
        if self._running:
            logger.warning("Stream processor already running")
            return

        if not self._detector.is_loaded:
            self._detector.load_model()

        self._camera.start()
        self._running = True
        self._start_time = time.monotonic()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("Stream processor started")

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        self._camera.stop()
        self._start_time = 0.0
        self._fps = 0.0
        logger.info("Stream processor stopped")

    def get_jpeg_frame(self) -> bytes:
        with self._lock:
            return self._current_jpeg

    def generate_mjpeg(self) -> Generator[bytes, None, None]:
        while self._running:
            frame = self.get_jpeg_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            time.sleep(0.03)

    def _process_loop(self) -> None:
        frame_count = 0
        fps_timer = time.monotonic()

        while self._running:
            frame = self._camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            detections = self._detector.detect(frame)
            annotated = self._detector.annotate_frame(frame, detections)

            violations = [d for d in detections if d.class_name in VIOLATION_CLASSES]
            is_compliant = len(violations) == 0
            self._alert_manager.record_frame(compliant=is_compliant)

            for v in violations:
                self._alert_manager.add_alert(v.class_name, v.confidence, frame)

            success, buffer = cv2.imencode(".jpg", annotated)
            if success:
                jpeg_bytes: bytes = buffer.tobytes()
                with self._lock:
                    self._current_jpeg = jpeg_bytes

            frame_count += 1
            elapsed = time.monotonic() - fps_timer
            if elapsed >= 1.0:
                self._fps = round(frame_count / elapsed, 1)
                frame_count = 0
                fps_timer = time.monotonic()

        logger.debug("Process loop exited")

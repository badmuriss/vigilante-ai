from __future__ import annotations

import logging
import sys
import threading
import time

import cv2
import numpy as np
from numpy.typing import NDArray

from app.config import settings

logger = logging.getLogger(__name__)


class CameraManager:
    def __init__(self) -> None:
        self._capture: cv2.VideoCapture | None = None
        self._frame: NDArray[np.uint8] | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._stop_event.set()  # Start in stopped state
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set()

    def start(self) -> None:
        if self.is_running:
            logger.warning("Camera is already running")
            return

        if sys.platform.startswith("win"):
            self._capture = cv2.VideoCapture(settings.CAMERA_INDEX, cv2.CAP_DSHOW)
        else:
            self._capture = cv2.VideoCapture(settings.CAMERA_INDEX)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAMERA_WIDTH)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAMERA_HEIGHT)
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            logger.error("Failed to open camera at index %d", settings.CAMERA_INDEX)
            raise RuntimeError(f"Cannot open camera at index {settings.CAMERA_INDEX}")

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(
            "Camera started (index=%d, %dx%d)",
            settings.CAMERA_INDEX,
            settings.CAMERA_WIDTH,
            settings.CAMERA_HEIGHT,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        with self._lock:
            self._frame = None
        logger.info("Camera stopped")

    def get_frame(self) -> NDArray[np.uint8] | None:
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set() and self._capture is not None:
            ret, frame = self._capture.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                self._stop_event.wait(0.01)
                continue
            with self._lock:
                self._frame = np.asarray(frame, dtype=np.uint8)
        logger.debug("Capture loop exited")

from __future__ import annotations

import base64
import threading
from collections import Counter, deque
from datetime import datetime
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from app.config import settings
from app.models import Alert


class AlertManager:
    MAX_ALERTS: int = 50

    def __init__(self) -> None:
        self._alerts: deque[Alert] = deque(maxlen=self.MAX_ALERTS)
        self._lock = threading.Lock()
        self._cooldowns: dict[str, datetime] = {}
        self._session_start: datetime = datetime.now()
        self._total_frames: int = 0
        self._compliant_frames: int = 0

    def _is_on_cooldown(self, violation_type: str) -> bool:
        with self._lock:
            last = self._cooldowns.get(violation_type)
        if last is None:
            return False
        elapsed = (datetime.now() - last).total_seconds()
        return elapsed < settings.ALERT_COOLDOWN_SECONDS

    @staticmethod
    def _make_thumbnail(frame: NDArray[np.uint8]) -> str:
        small = cv2.resize(frame, (160, 120))
        success, buffer = cv2.imencode(".jpg", small)
        if not success:
            return ""
        return base64.b64encode(buffer.tobytes()).decode("utf-8")

    def add_alert(
        self,
        violation_type: str,
        confidence: float,
        frame: NDArray[np.uint8],
    ) -> Alert | None:
        if self._is_on_cooldown(violation_type):
            return None

        thumbnail = self._make_thumbnail(frame)
        alert = Alert(
            violation_type=violation_type,
            confidence=confidence,
            frame_thumbnail=thumbnail,
        )

        with self._lock:
            self._alerts.appendleft(alert)
            self._cooldowns[violation_type] = datetime.now()

        return alert

    def get_alerts(self) -> list[Alert]:
        with self._lock:
            return list(self._alerts)

    def clear_alerts(self) -> None:
        with self._lock:
            self._alerts.clear()
            self._cooldowns.clear()

    def reset_session(self) -> None:
        """Clear all alerts, cooldowns, counters, and reset session start."""
        with self._lock:
            self._alerts.clear()
            self._cooldowns.clear()
            self._total_frames = 0
            self._compliant_frames = 0
            self._session_start = datetime.now()

    def record_frame(self, *, compliant: bool) -> None:
        with self._lock:
            self._total_frames += 1
            if compliant:
                self._compliant_frames += 1

    def get_violations_timeline(self) -> list[dict[str, Any]]:
        with self._lock:
            alerts = list(self._alerts)
        minute_counts: Counter[datetime] = Counter()
        for alert in alerts:
            minute_key = alert.timestamp.replace(second=0, microsecond=0)
            minute_counts[minute_key] += 1
        timeline = [
            {"timestamp": ts, "count": count}
            for ts, count in sorted(minute_counts.items())
        ]
        return timeline

    def get_stats(self) -> dict[str, object]:
        session_duration = (datetime.now() - self._session_start).total_seconds()
        with self._lock:
            total_violations = len(self._alerts)
            total_frames = self._total_frames
            compliant_frames = self._compliant_frames
        compliance_rate = (
            (compliant_frames / total_frames * 100.0)
            if total_frames > 0
            else 100.0
        )
        return {
            "total_violations": total_violations,
            "session_duration_seconds": round(session_duration, 1),
            "compliance_rate": round(compliance_rate, 1),
            "violations_timeline": self.get_violations_timeline(),
        }

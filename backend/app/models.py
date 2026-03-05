from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]


@dataclass
class Alert:
    violation_type: str
    confidence: float
    frame_thumbnail: str
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

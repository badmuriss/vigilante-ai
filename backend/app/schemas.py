from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: str
    timestamp: datetime
    violation_type: str
    confidence: float
    frame_thumbnail: str


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]


class ClearAlertsResponse(BaseModel):
    cleared: bool


class ViolationTimelineEntry(BaseModel):
    timestamp: datetime
    count: int


class StatsResponse(BaseModel):
    total_violations: int
    session_duration_seconds: float
    compliance_rate: float
    violations_timeline: list[ViolationTimelineEntry]
